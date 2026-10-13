import pytest
import logging
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.buildings import Building
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.ladders import Ladder
from app.models.shelf_positions import ShelfPosition
from app.models.shelf_types import ShelfType
from app.models.side_orientations import SideOrientation
from app.models.owners import Owner

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_location_hierarchy(session, suffix=""):
    """Build Building → Module → Aisle → Side → Ladder and return the ladder."""
    building = Building(name=f"Test Building {suffix}")
    session.add(building)
    session.commit()

    module = Module(module_number=f"M{suffix}", building_id=building.id)
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

    return ladder


def _override_auth(app):
    """Install a mock auth dependency that grants all permissions."""
    from app.auth.dependencies import get_current_user_with_permissions

    global_mock = app.dependency_overrides.get(get_current_user_with_permissions)

    def _mock():
        class P:
            name = "can_manage_locations"
        class G:
            permissions = [P()]
        class U:
            groups = [G()]
        return U()

    app.dependency_overrides[get_current_user_with_permissions] = _mock
    return get_current_user_with_permissions, global_mock


# ---------------------------------------------------------------------------
# A. Location Hierarchy Tests
# ---------------------------------------------------------------------------

def test_location_uniqueness(test_database, session):
    """
    Validate that trying to create two "Aisle 1"s inside the same Module throws an IntegrityError, 
    but creating "Aisle 1" in Module A and "Aisle 1" in Module B succeeds.
    """
    building = Building(name="Aisle Test Building")
    session.add(building)
    session.commit()
    
    module_a = Module(module_number="A", building_id=building.id)
    module_b = Module(module_number="B", building_id=building.id)
    session.add_all([module_a, module_b])
    session.commit()

    aisle_1_mod_a = Aisle(aisle_number=1, module_id=module_a.id)
    session.add(aisle_1_mod_a)
    session.commit()

    # Duplicate in same Module → must fail
    duplicate_aisle = Aisle(aisle_number=1, module_id=module_a.id)
    session.add(duplicate_aisle)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    # Same number but different Module → must succeed
    aisle_1_mod_b = Aisle(aisle_number=1, module_id=module_b.id)
    session.add(aisle_1_mod_b)
    session.commit()
    
    assert aisle_1_mod_b.id is not None
    assert aisle_1_mod_a.id != aisle_1_mod_b.id


def test_building_delete_protection(test_database, session):
    """
    Ensure that deleting a Building cascades deletions to Modules, Aisles, and Sides.
    """
    building = Building(name="Cascade Test Building")
    session.add(building)
    session.commit()
    
    module = Module(module_number="Cascade", building_id=building.id)
    session.add(module)
    session.commit()
    
    aisle = Aisle(aisle_number=99, module_id=module.id)
    session.add(aisle)
    session.commit()
    
    orientation = session.query(SideOrientation).filter_by(name="Left").first()
    assert orientation is not None, "A SideOrientation must exist from seed data."

    side = Side(side_orientation_id=orientation.id, aisle_id=aisle.id)
    session.add(side)
    session.commit()
    
    building_id, module_id, aisle_id, side_id = building.id, module.id, aisle.id, side.id
    
    session.delete(building)
    session.commit()
    
    assert session.query(Building).filter_by(id=building_id).first() is None
    assert session.query(Module).filter_by(id=module_id).first() is None
    assert session.query(Aisle).filter_by(id=aisle_id).first() is None
    assert session.query(Side).filter_by(id=side_id).first() is None


def test_shelf_creation_positions(client: TestClient, session: Session, test_database):
    """
    Verify that creating a Shelf via POST /shelves/ generates exactly max_capacity ShelfPositions.
    """
    from app.main import app

    dep_key, global_mock = _override_auth(app)
    try:
        shelf_type = session.query(ShelfType).first()
        assert shelf_type is not None, "A ShelfType must exist for this test."

        ladder = _create_location_hierarchy(session, suffix="SP1")
        owner = session.query(Owner).first()
        assert owner is not None

        response = client.post("/shelves/", json={
            "barcode_value": "12345",
            "height": "12.50", "width": "36.00", "depth": "18.00",
            "shelf_number": 1,
            "shelf_type_id": shelf_type.id,
            "ladder_id": ladder.id,
            "owner_id": owner.id,
        })
        assert response.status_code == 201, f"Shelf creation failed: {response.json()}"

        shelf_id = response.json()["id"]
        positions = session.query(ShelfPosition).filter_by(shelf_id=shelf_id).all()

        assert len(positions) == shelf_type.max_capacity
        assert sorted(p.position_number for p in positions) == list(range(1, shelf_type.max_capacity + 1))
    finally:
        if global_mock:
            app.dependency_overrides[dep_key] = global_mock
        else:
            app.dependency_overrides.pop(dep_key, None)


def test_shelf_edit_size_class_update(client: TestClient, session: Session, test_database):
    """
    When a Shelf's shelf_type is changed via PATCH /shelves/{id}, the endpoint should
    adjust ShelfPositions to match the new max_capacity (adding or removing positions).
    """
    from app.main import app

    dep_key, global_mock = _override_auth(app)
    try:
        # Pick two shelf types with DIFFERENT max_capacities
        shelf_types = session.query(ShelfType).order_by(ShelfType.id).all()
        assert len(shelf_types) >= 2, "Need ≥2 ShelfTypes for size-class edit test."

        type_a = shelf_types[0]  # max_capacity = 8
        # Find one with a different capacity
        type_b = next((st for st in shelf_types if st.max_capacity != type_a.max_capacity), None)
        if type_b is None:
            # All same capacity — just pick a different one and test that positions stay the same
            type_b = shelf_types[1]

        ladder = _create_location_hierarchy(session, suffix="EDIT")
        owner = session.query(Owner).first()

        # 1. Create shelf with type_a
        resp = client.post("/shelves/", json={
            "barcode_value": "22345",
            "height": "12.50", "width": "36.00", "depth": "18.00",
            "shelf_number": 1,
            "shelf_type_id": type_a.id,
            "ladder_id": ladder.id,
            "owner_id": owner.id,
        })
        assert resp.status_code == 201, f"Shelf creation failed: {resp.json()}"
        shelf_id = resp.json()["id"]

        positions_before = session.query(ShelfPosition).filter_by(shelf_id=shelf_id).count()
        assert positions_before == type_a.max_capacity

        # 2. PATCH to change shelf_type
        patch_resp = client.patch(f"/shelves/{shelf_id}", json={
            "shelf_type_id": type_b.id,
        })
        assert patch_resp.status_code == 200, f"Shelf update failed: {patch_resp.json()}"

        # 3. Verify positions match new capacity
        # Expire cached objects so we re-query
        session.expire_all()
        positions_after = session.query(ShelfPosition).filter_by(shelf_id=shelf_id).count()
        assert positions_after == type_b.max_capacity, (
            f"Expected {type_b.max_capacity} positions after edit, got {positions_after}"
        )
    finally:
        if global_mock:
            app.dependency_overrides[dep_key] = global_mock
        else:
            app.dependency_overrides.pop(dep_key, None)


def test_bulk_shelf_creation_positions(client: TestClient, session: Session, test_database):
    """
    When creating multiple shelves via separate POST /shelves/ calls,
    verify each shelf independently receives the correct number of positions.
    """
    from app.main import app

    dep_key, global_mock = _override_auth(app)
    try:
        shelf_types = session.query(ShelfType).order_by(ShelfType.id).limit(2).all()
        assert len(shelf_types) >= 1

        ladder = _create_location_hierarchy(session, suffix="BULK")
        owner = session.query(Owner).first()

        created_shelves = []
        for i, st in enumerate(shelf_types):
            resp = client.post("/shelves/", json={
                "barcode_value": f"{30000 + i}",
                "height": "12.50", "width": "36.00", "depth": "18.00",
                "shelf_number": i + 1,
                "shelf_type_id": st.id,
                "ladder_id": ladder.id,
                "owner_id": owner.id,
            })
            assert resp.status_code == 201, f"Shelf {i+1} creation failed: {resp.json()}"
            created_shelves.append((resp.json()["id"], st.max_capacity))

        # Verify each shelf has the correct number of positions
        for shelf_id, expected_cap in created_shelves:
            count = session.query(ShelfPosition).filter_by(shelf_id=shelf_id).count()
            assert count == expected_cap, (
                f"Shelf {shelf_id}: expected {expected_cap} positions, got {count}"
            )
    finally:
        if global_mock:
            app.dependency_overrides[dep_key] = global_mock
        else:
            app.dependency_overrides.pop(dep_key, None)


def test_bulk_shelf_edit_size_class_update(client: TestClient, session: Session, test_database):
    """
    When shelf_type_id is changed via PATCH /shelves/bulk, the endpoint should
    adjust positions to match the new max_capacity, just like the single-shelf PATCH.
    """
    from app.main import app

    dep_key, global_mock = _override_auth(app)
    try:
        shelf_types = session.query(ShelfType).order_by(ShelfType.id).all()
        assert len(shelf_types) >= 2

        type_a = shelf_types[0]
        # Find a type with a different capacity for a meaningful test
        type_b = next((st for st in shelf_types if st.max_capacity != type_a.max_capacity), shelf_types[1])

        ladder = _create_location_hierarchy(session, suffix="BULKE")
        owner = session.query(Owner).first()

        # Create two shelves with type_a via the API (which creates positions)
        shelf_ids = []
        for i in range(2):
            resp = client.post("/shelves/", json={
                "barcode_value": f"{40000 + i}",
                "height": "12.50", "width": "36.00", "depth": "18.00",
                "shelf_number": i + 1,
                "shelf_type_id": type_a.id,
                "ladder_id": ladder.id,
                "owner_id": owner.id,
            })
            assert resp.status_code == 201
            shelf_ids.append(resp.json()["id"])

        # Verify initial positions match type_a capacity
        for sid in shelf_ids:
            count = session.query(ShelfPosition).filter_by(shelf_id=sid).count()
            assert count == type_a.max_capacity

        # Bulk update shelf_type to type_b via API
        bulk_payload = [{"id": sid, "shelf_type_id": type_b.id} for sid in shelf_ids]
        bulk_resp = client.patch("/shelves/bulk", json=bulk_payload)
        assert bulk_resp.status_code == 200, f"Bulk update failed: {bulk_resp.json()}"

        # Verify positions now match type_b capacity
        session.expire_all()
        for sid in shelf_ids:
            new_count = session.query(ShelfPosition).filter_by(shelf_id=sid).count()
            assert new_count == type_b.max_capacity, (
                f"Shelf {sid}: expected {type_b.max_capacity} positions after bulk edit, got {new_count}"
            )
    finally:
        if global_mock:
            app.dependency_overrides[dep_key] = global_mock
        else:
            app.dependency_overrides.pop(dep_key, None)


def test_position_occupancy(session: Session, test_database):
    """
    When a Tray is assigned to a ShelfPosition, assigning a second Tray to
    the same position must fail due to the one-to-one FK constraint.
    """
    from app.models.shelves import Shelf
    from app.models.trays import Tray
    from app.models.barcodes import Barcode
    from app.models.barcode_types import BarcodeType
    from app.models.size_class import SizeClass

    ladder = _create_location_hierarchy(session, suffix="OCC")
    owner = session.query(Owner).first()
    shelf_type = session.query(ShelfType).first()

    # Create a shelf directly via ORM (no API needed for this constraint test)
    shelf = Shelf(
        shelf_number=1,
        ladder_id=ladder.id,
        shelf_type_id=shelf_type.id,
        owner_id=owner.id,
        height=12.50, width=36.00, depth=18.00,
        available_space=shelf_type.max_capacity,
    )
    session.add(shelf)
    session.commit()

    # Create a position on that shelf
    pos = ShelfPosition(shelf_id=shelf.id, position_number=1)
    session.add(pos)
    session.commit()

    # Create two barcodes for two trays
    tray_barcode_type = session.query(BarcodeType).filter_by(name="Tray").first()
    assert tray_barcode_type is not None

    bc1 = Barcode(value="AB12345", type_id=tray_barcode_type.id, withdrawn=False)
    bc2 = Barcode(value="CD67890", type_id=tray_barcode_type.id, withdrawn=False)
    session.add_all([bc1, bc2])
    session.commit()

    size_class = session.query(SizeClass).first()

    # Assign Tray 1 to the position
    tray1 = Tray(
        barcode_id=bc1.id,
        shelf_position_id=pos.id,
        owner_id=owner.id,
        size_class_id=size_class.id,
    )
    session.add(tray1)
    session.commit()

    # Attempt to assign Tray 2 to the SAME position → must fail
    tray2 = Tray(
        barcode_id=bc2.id,
        shelf_position_id=pos.id,
        owner_id=owner.id,
        size_class_id=size_class.id,
    )
    session.add(tray2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
