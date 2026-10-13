"""
DB-backed integration tests for the shelving placement algorithm:
ShelvingAssignmentService.pre_assign_containers / _find_available_positions.

A fresh Building is created per test so the building-scoped position search is
fully isolated from seed data. Pure validation rules are covered separately in
tests/unit/test_shelving_validation.py.
"""
import uuid

from app.models.aisles import Aisle
from app.models.barcode_types import BarcodeType
from app.models.barcodes import Barcode
from app.models.buildings import Building
from app.models.ladders import Ladder
from app.models.modules import Module
from app.models.owners import Owner
from app.models.shelf_positions import ShelfPosition
from app.models.shelf_types import ShelfType
from app.models.shelves import Shelf
from app.models.shelving_job_containers import (
    ShelvingJobContainer,
    ShelvingJobContainerStatus,
)
from app.models.shelving_jobs import ShelvingJob, ShelvingJobStatus
from app.models.side_orientations import SideOrientation
from app.models.sides import Side
from app.models.size_class import SizeClass
from app.models.trays import Tray
from app.services.shelving_assignment import shelving_assignment_service


# --------------------------------------------------------------------------- #
# Scenario builders
# --------------------------------------------------------------------------- #
def _build_location(session):
    building = Building(name=f"PlaceBldg-{uuid.uuid4().hex[:8]}")
    session.add(building)
    session.commit()

    module = Module(module_number=f"M{uuid.uuid4().hex[:6]}", building_id=building.id)
    session.add(module)
    session.commit()

    aisle = Aisle(aisle_number=1, module_id=module.id)
    session.add(aisle)
    session.commit()

    orientation = session.query(SideOrientation).filter_by(name="Left").first()
    side = Side(side_orientation_id=orientation.id, aisle_id=aisle.id)
    session.add(side)
    session.commit()

    ladder = Ladder(ladder_number=1, side_id=side.id)
    session.add(ladder)
    session.commit()

    return building, ladder


def _make_shelf(session, ladder, owner, size_class, *, height, num_positions):
    shelf_type = ShelfType(
        type=f"ST-{uuid.uuid4().hex[:8]}",
        size_class_id=size_class.id,
        max_capacity=num_positions,
    )
    session.add(shelf_type)
    session.commit()

    shelf = Shelf(
        shelf_number=1,
        ladder_id=ladder.id,
        shelf_type_id=shelf_type.id,
        owner_id=owner.id,
        height=height,
        width=36.00,
        depth=18.00,
        available_space=num_positions,
    )
    session.add(shelf)
    session.commit()

    positions = [
        ShelfPosition(shelf_id=shelf.id, position_number=i)
        for i in range(1, num_positions + 1)
    ]
    session.add_all(positions)
    session.commit()
    return shelf, positions


def _make_barcode(session):
    # Trays require a barcode (DB check constraint: barcode XOR withdrawn-barcode).
    barcode_type = session.query(BarcodeType).filter_by(name="Tray").first()
    barcode = Barcode(value=uuid.uuid4().hex[:20], type_id=barcode_type.id, withdrawn=False)
    session.add(barcode)
    session.commit()
    return barcode


def _make_job_with_trays(session, building, owner, size_class, count):
    job = ShelvingJob(building_id=building.id, status=ShelvingJobStatus.Created)
    session.add(job)
    session.commit()

    for _ in range(count):
        tray = Tray(
            size_class_id=size_class.id,
            owner_id=owner.id,
            barcode_id=_make_barcode(session).id,
        )
        session.add(tray)
        session.commit()
        session.add(
            ShelvingJobContainer(
                shelving_job_id=job.id,
                tray_id=tray.id,
                status=ShelvingJobContainerStatus.PENDING,
            )
        )
    session.commit()
    return job


def _containers(session, job_id):
    return session.query(ShelvingJobContainer).filter_by(shelving_job_id=job_id).all()


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_pre_assign_assigns_matching_positions(session, test_database):
    owner = session.query(Owner).first()
    size_class = session.query(SizeClass).first()
    building, ladder = _build_location(session)
    _, positions = _make_shelf(
        session, ladder, owner, size_class,
        height=size_class.height + 5, num_positions=3,
    )
    job = _make_job_with_trays(session, building, owner, size_class, count=2)

    result = shelving_assignment_service.pre_assign_containers(
        session=session, shelving_job_id=job.id, building_id=building.id
    )

    assert result.assigned_count == 2
    assert result.unassigned_count == 0

    session.expire_all()
    refreshed = _containers(session, job.id)
    assert all(c.status == ShelvingJobContainerStatus.ASSIGNED for c in refreshed)
    assert all(c.position_reserved_at is not None for c in refreshed)
    proposed = {c.proposed_shelf_position_id for c in refreshed}
    assert len(proposed) == 2  # distinct positions, no double-booking
    assert proposed.issubset({p.id for p in positions})


def test_pre_assign_partial_when_insufficient_positions(session, test_database):
    owner = session.query(Owner).first()
    size_class = session.query(SizeClass).first()
    building, ladder = _build_location(session)
    _make_shelf(
        session, ladder, owner, size_class,
        height=size_class.height + 5, num_positions=2,
    )
    job = _make_job_with_trays(session, building, owner, size_class, count=3)

    result = shelving_assignment_service.pre_assign_containers(
        session=session, shelving_job_id=job.id, building_id=building.id
    )

    assert result.assigned_count == 2
    assert result.unassigned_count == 1
    assert len(result.unassigned_barcodes) == 1

    session.expire_all()
    statuses = sorted(c.status for c in _containers(session, job.id))
    assert statuses == [
        ShelvingJobContainerStatus.ASSIGNED,
        ShelvingJobContainerStatus.ASSIGNED,
        ShelvingJobContainerStatus.UNASSIGNED,
    ]


def test_pre_assign_excludes_too_short_shelves(session, test_database):
    owner = session.query(Owner).first()
    size_class = session.query(SizeClass).first()
    building, ladder = _build_location(session)
    # Shelf strictly shorter than the size class → fails the physical-fit filter.
    _make_shelf(
        session, ladder, owner, size_class,
        height=size_class.height / 2, num_positions=2,
    )
    job = _make_job_with_trays(session, building, owner, size_class, count=1)

    result = shelving_assignment_service.pre_assign_containers(
        session=session, shelving_job_id=job.id, building_id=building.id
    )

    assert result.assigned_count == 0
    assert result.unassigned_count == 1


def test_pre_assign_skips_occupied_positions(session, test_database):
    owner = session.query(Owner).first()
    size_class = session.query(SizeClass).first()
    building, ladder = _build_location(session)
    _, positions = _make_shelf(
        session, ladder, owner, size_class,
        height=size_class.height + 5, num_positions=2,
    )
    # Occupy the first position with an already-shelved tray.
    occupying_tray = Tray(
        size_class_id=size_class.id,
        owner_id=owner.id,
        shelf_position_id=positions[0].id,
        barcode_id=_make_barcode(session).id,
    )
    session.add(occupying_tray)
    session.commit()

    job = _make_job_with_trays(session, building, owner, size_class, count=1)

    result = shelving_assignment_service.pre_assign_containers(
        session=session, shelving_job_id=job.id, building_id=building.id
    )

    assert result.assigned_count == 1
    session.expire_all()
    container = _containers(session, job.id)[0]
    assert container.proposed_shelf_position_id == positions[1].id
