"""
Section B: Inventory Entity Tests
Validates barcode uniqueness, shelf capacity enforcement,
item–tray mutual-exclusivity, and non-tray-item vs. item distinction.
"""
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.buildings import Building
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.ladders import Ladder
from app.models.shelves import Shelf
from app.models.shelf_positions import ShelfPosition
from app.models.shelf_types import ShelfType
from app.models.side_orientations import SideOrientation
from app.models.owners import Owner
from app.models.barcodes import Barcode
from app.models.barcode_types import BarcodeType
from app.models.trays import Tray
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.size_class import SizeClass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_hierarchy_with_shelf(session, suffix=""):
    """Build Building → … → Shelf with positions via ORM, return the shelf."""
    building = Building(name=f"Inv Building {suffix}")
    session.add(building)
    session.commit()

    module = Module(module_number=f"I{suffix}", building_id=building.id)
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

    shelf_type = session.query(ShelfType).first()
    owner = session.query(Owner).first()

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

    # Create positions 1..max_capacity
    for i in range(1, shelf_type.max_capacity + 1):
        session.add(ShelfPosition(shelf_id=shelf.id, position_number=i))
    session.commit()

    return shelf


def _make_barcode(session, value, type_name="Item"):
    """Create and return a Barcode with the given value and type."""
    bt = session.query(BarcodeType).filter_by(name=type_name).first()
    bc = Barcode(value=value, type_id=bt.id, withdrawn=False)
    session.add(bc)
    session.commit()
    return bc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_barcode_unique_assignment(session: Session, test_database):
    """
    The Barcode.value column has a UNIQUE constraint.
    Creating two Barcodes with the same value must raise IntegrityError.
    """
    bt = session.query(BarcodeType).filter_by(name="Item").first()
    assert bt is not None

    bc1 = Barcode(value="UNIQUE001", type_id=bt.id, withdrawn=False)
    session.add(bc1)
    session.commit()

    # Attempting a duplicate value must fail
    bc2 = Barcode(value="UNIQUE001", type_id=bt.id, withdrawn=False)
    session.add(bc2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    # A different value succeeds
    bc3 = Barcode(value="UNIQUE002", type_id=bt.id, withdrawn=False)
    session.add(bc3)
    session.commit()
    assert bc3.id is not None


def test_shelf_capacity_by_size_class(session: Session, test_database):
    """
    A Shelf's number of ShelfPositions is determined by its ShelfType.max_capacity.
    After creating positions, the count must equal max_capacity.
    Also verifies calc_available_space() returns the correct value when
    the shelf is fully empty.
    """
    shelf = _create_hierarchy_with_shelf(session, suffix="CAP")
    shelf_type = session.query(ShelfType).get(shelf.shelf_type_id)

    positions = session.query(ShelfPosition).filter_by(shelf_id=shelf.id).all()
    assert len(positions) == shelf_type.max_capacity

    # All positions are empty → available space should equal max_capacity
    avail = shelf.calc_available_space(session=session)
    assert avail == shelf_type.max_capacity


def test_item_tray_mutual_exclusivity(session: Session, test_database):
    """
    An Item belongs to exactly one Tray via tray_id FK.
    Two Items can reference different Trays, but if we try to assign a Tray's
    barcode to a second Tray (simulating duplication), the unique barcode_id
    constraint prevents it.
    """
    shelf = _create_hierarchy_with_shelf(session, suffix="MUT")
    owner = session.query(Owner).first()
    size_class = session.query(SizeClass).first()

    # Position for the tray
    pos = session.query(ShelfPosition).filter_by(shelf_id=shelf.id).first()

    # Create a tray with a unique barcode
    tray_bc = _make_barcode(session, "TR00001", type_name="Tray")
    tray = Tray(
        barcode_id=tray_bc.id,
        shelf_position_id=pos.id,
        owner_id=owner.id,
        size_class_id=size_class.id,
    )
    session.add(tray)
    session.commit()

    # Create an item inside the tray
    item_bc = _make_barcode(session, "1234567890A", type_name="Item")
    item = Item(
        barcode_id=item_bc.id,
        tray_id=tray.id,
        owner_id=owner.id,
        size_class_id=size_class.id,
    )
    session.add(item)
    session.commit()

    assert item.tray_id == tray.id

    # Attempting to create ANOTHER tray with the SAME barcode must fail
    dup_tray = Tray(
        barcode_id=tray_bc.id,  # same barcode — violates unique constraint
        owner_id=owner.id,
        size_class_id=size_class.id,
    )
    session.add(dup_tray)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_non_tray_item_vs_item(session: Session, test_database):
    """
    Items and NonTrayItems are distinct entity types that must live on separate
    shelves. In production, cross-entity barcode uniqueness is enforced by the
    barcodes.value UNIQUE constraint: every Item and NonTrayItem gets its own
    Barcode record, and no two Barcode records can share the same value.

    This test:
    1. Creates an Item with barcode value "SHARED-BC-001" on shelf 1.
    2. Creates a NonTrayItem with a different barcode on shelf 2 (success).
    3. Attempts to create a SECOND Barcode with value "SHARED-BC-001" for a
       new NonTrayItem — this must fail with IntegrityError (production behavior).
    """
    # Separate shelf for the Tray (Items go inside Trays)
    shelf_tray = _create_hierarchy_with_shelf(session, suffix="NTI1")
    # Separate shelf for the NonTrayItem
    shelf_nti = _create_hierarchy_with_shelf(session, suffix="NTI2")

    owner = session.query(Owner).first()
    size_class = session.query(SizeClass).first()

    tray_pos = session.query(ShelfPosition).filter_by(shelf_id=shelf_tray.id).first()
    nti_pos = session.query(ShelfPosition).filter_by(shelf_id=shelf_nti.id).first()

    # --- Step 1: Create a Tray on shelf 1 with an Item inside ---
    tray_bc = _make_barcode(session, "TR10001", type_name="Tray")
    tray = Tray(
        barcode_id=tray_bc.id,
        shelf_position_id=tray_pos.id,
        owner_id=owner.id,
        size_class_id=size_class.id,
    )
    session.add(tray)
    session.commit()

    shared_barcode_value = "SHARED-BC-001"
    item_bc = _make_barcode(session, shared_barcode_value, type_name="Item")
    item = Item(
        barcode_id=item_bc.id,
        tray_id=tray.id,
        owner_id=owner.id,
        size_class_id=size_class.id,
    )
    session.add(item)
    session.commit()
    assert item.tray_id == tray.id

    # --- Step 2: Create a NonTrayItem on shelf 2 with a DIFFERENT barcode ---
    nti_bc = _make_barcode(session, "NTI-UNIQUE-001", type_name="Item")
    nti = NonTrayItem(
        barcode_id=nti_bc.id,
        shelf_position_id=nti_pos.id,
        owner_id=owner.id,
        size_class_id=size_class.id,
    )
    session.add(nti)
    session.commit()

    assert nti.shelf_position_id == nti_pos.id
    assert item.id != nti.id  # fundamentally different entities

    # --- Step 3: Try to create a barcode with the SAME value as the Item's ---
    # This is the production behavior: the barcodes.value UNIQUE constraint
    # prevents a NonTrayItem from ever being created with a duplicate barcode.
    bt = session.query(BarcodeType).filter_by(name="Item").first()
    duplicate_bc = Barcode(value=shared_barcode_value, type_id=bt.id, withdrawn=False)
    session.add(duplicate_bc)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
