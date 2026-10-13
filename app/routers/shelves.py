# /code/app/routers/shelves.py - REFACTORED: Removed ShelfNumber/ShelfPositionNumber lookup table dependencies

import logging
import re
from typing import List, Optional

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination import paginate as paginate_list
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams, ShelfFilterParams
from app.models.owners import Owner
from app.models.shelf_types import ShelfType
from app.models.shelves import Shelf
from app.models.barcodes import Barcode
from app.models.buildings import Building
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.ladders import Ladder
from app.models.size_class import SizeClass
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.shelf_positions import ShelfPosition
from app.schemas.shelves import (
    ShelfInput,
    ShelfUpdateInput,
    ShelfBulkUpdateInput,
    ShelfListOutput,
    ShelfDetailWriteOutput,
    ShelfDetailReadOutput,
    ShelfInsertOutput,
)
from app.config.exceptions import NotFound, ValidationException, InternalServerError
from app.sorting import ShelvingSorter
from app.utilities import start_session_with_audit_info

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.services.audit_service import log_audit_event, AuditEventType

router = APIRouter(
    prefix="/shelves",
    tags=["shelves"],
    dependencies=[Depends(get_current_user_with_permissions)],
)

LOGGER = logging.getLogger("app.routers.shelves")


def _adjust_shelf_positions(session: Session, shelf_id: int, old_type_id: int, new_type_id: int):
    """
    Adjust ShelfPosition records when a shelf's shelf_type changes.
    Adds positions if the new capacity is larger, removes empty positions
    from the end if the new capacity is smaller.
    Raises ValidationException if occupied positions would be removed.
    """
    old_shelf_type = session.get(ShelfType, old_type_id)
    new_shelf_type = session.get(ShelfType, new_type_id)

    if not new_shelf_type:
        raise ValidationException(detail=f"New Shelf Type ID {new_type_id} not found.")

    old_capacity = old_shelf_type.max_capacity if old_shelf_type else 0
    new_capacity = new_shelf_type.max_capacity

    if new_capacity == old_capacity:
        return

    # --- DECREASING CAPACITY ---
    if new_capacity < old_capacity:
        num_to_remove = old_capacity - new_capacity

        positions_to_check_query = (
            select(ShelfPosition)
            .where(ShelfPosition.shelf_id == shelf_id)
            .order_by(ShelfPosition.position_number.desc())
            .limit(num_to_remove)
        )
        positions_to_delete = session.execute(positions_to_check_query).scalars().all()
        position_ids_to_delete = [p.id for p in positions_to_delete]

        if position_ids_to_delete:
            occupied_tray = session.execute(
                select(Tray.id).where(Tray.shelf_position_id.in_(position_ids_to_delete)).limit(1)
            ).first()
            occupied_non_tray = session.execute(
                select(NonTrayItem.id).where(NonTrayItem.shelf_position_id.in_(position_ids_to_delete)).limit(1)
            ).first()

            if occupied_tray or occupied_non_tray:
                raise ValidationException(detail="Shelf is not Empty")

            for pos in positions_to_delete:
                session.delete(pos)

    # --- INCREASING CAPACITY ---
    elif new_capacity > old_capacity:
        for position_num in range(old_capacity + 1, new_capacity + 1):
            session.add(ShelfPosition(
                shelf_id=shelf_id,
                position_number=position_num,
            ))


@router.get("/", response_model=Page[ShelfListOutput])
def get_shelf_list(
    session: Session = Depends(get_session),
    params: ShelfFilterParams = Depends(),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Shelf location"),
) -> list:
    """
    Get a list of shelves.
    """
    shelf_queryset = select(Shelf)

    if search:
        shelf_queryset = shelf_queryset.where(Shelf.location.icontains(search))

    if params.owner_id:
        shelf_queryset = shelf_queryset.where(Shelf.owner_id == params.owner_id)

    if params.size_class_id:
        shelf_queryset = shelf_queryset.join(
            ShelfType, Shelf.shelf_type_id == ShelfType.id
        ).where(ShelfType.size_class_id == params.size_class_id)

    # location from most to least constrained
    if params.shelf_id:
        shelf_queryset = shelf_queryset.where(Shelf.id == params.shelf_id)
    elif params.ladder_id:
        shelf_queryset = shelf_queryset.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).where(Ladder.id == params.ladder_id)
    elif params.side_id:
        shelf_queryset = (
            shelf_queryset.join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .where(Side.id == params.side_id)
        )
    elif params.aisle_id:
        shelf_queryset = (
            shelf_queryset.join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .where(Aisle.id == params.aisle_id)
        )
    elif params.module_id:
        shelf_queryset = (
            shelf_queryset.join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .join(Module, Aisle.module_id == Module.id)
            .where(Module.id == params.module_id)
        )
    elif params.building_id:
        shelf_queryset = (
            shelf_queryset.join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .join(Module, Aisle.module_id == Module.id)
            .join(Building, Module.building_id == Building.id)
            .where(Building.id == params.building_id)
        )

    if params.unassigned:
        shelf_queryset = shelf_queryset.where(Shelf.barcode_id == None)
    if params.barcode_value:
        barcode_value_subquery = select(Barcode.id).where(
            Barcode.value == params.barcode_value
        ).scalar_subquery()
        shelf_queryset = shelf_queryset.where(
            Shelf.barcode_id.in_(select(Barcode.id).where(Barcode.value == params.barcode_value))
        )
    if params.owner:
        owner_subquery = select(Owner.id).where(Owner.name == params.owner).scalar_subquery()
        shelf_queryset = shelf_queryset.where(Shelf.owner_id == owner_subquery)
    if params.size_class:
        size_class_subquery = select(SizeClass.id).where(
            SizeClass.name == params.size_class
        ).scalar_subquery()
        shelf_queryset = shelf_queryset.join(
            ShelfType, Shelf.shelf_type_id == ShelfType.id
        ).where(ShelfType.size_class_id == size_class_subquery)
    if params.location:
        shelf_queryset = shelf_queryset.where(Shelf.location == params.location)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = ShelvingSorter(Shelf)
        shelf_queryset = sorter.apply_sorting(shelf_queryset, sort_params)

    return paginate(session, shelf_queryset)


@router.get("/{id}", response_model=ShelfDetailReadOutput)
def get_shelf_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a shelf with the given ID.
    """
    shelf = session.get(Shelf, id)

    if shelf:
        return shelf

    raise NotFound(detail=f"Shelf ID {id} Not Found")


@router.get("/barcode/{value}", response_model=ShelfDetailReadOutput)
def get_shelf_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a shelf using a barcode value
    """
    statement = select(Shelf).join(Barcode).where(Barcode.value == value)
    shelf = session.execute(statement).scalars().first()
    if not shelf:
        raise NotFound(detail=f"Shelf with barcode value {value} not found")
    return shelf


def get_next_available_position(session: Session, shelf_id: int, direction: str = "low_to_high") -> Optional[int]:
    """
    Calculate the next available shelf position number.
    """
    positions_query = (
        select(ShelfPosition)
        .where(ShelfPosition.shelf_id == shelf_id)
    )
    
    if direction == "high_to_low":
        positions_query = positions_query.order_by(ShelfPosition.position_number.desc())
    else:
        positions_query = positions_query.order_by(ShelfPosition.position_number.asc())
    
    positions = session.execute(positions_query).scalars().all()
    
    for position in positions:
        # Check if position is occupied by a tray
        tray = session.execute(
            select(Tray.id).where(Tray.shelf_position_id == position.id).limit(1)
        ).scalar()
        
        if tray:
            continue
        
        # Check if position is occupied by a non-tray item
        non_tray = session.execute(
            select(NonTrayItem.id).where(NonTrayItem.shelf_position_id == position.id).limit(1)
        ).scalar()
        
        if non_tray:
            continue
        
        # Position is available
        return position.position_number
    
    # No available positions
    return None


@router.get("/barcode/{value}/next-position")
def get_shelf_next_available_position(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a shelf's next available position using a barcode value.
    """
    from app.routers.system_settings import get_setting_value
    
    statement = select(Shelf).join(Barcode).where(Barcode.value == value)
    shelf = session.execute(statement).scalars().first()
    if not shelf:
        raise NotFound(detail=f"Shelf with barcode value {value} not found")
    
    direction = get_setting_value(session, "shelf_position_auto_assign_direction", "low_to_high")
    next_position = get_next_available_position(session, shelf.id, direction)
    
    return {
        "shelf_id": shelf.id,
        "shelf_barcode_value": shelf.barcode.value if shelf.barcode else None,
        "owner_id": shelf.owner_id,
        "owner_name": shelf.owner.name if shelf.owner else None,
        "size_class_id": shelf.shelf_type.size_class_id if shelf.shelf_type else None,
        "size_class_name": shelf.shelf_type.size_class.name if shelf.shelf_type and shelf.shelf_type.size_class else None,
        "max_capacity": shelf.shelf_type.max_capacity if shelf.shelf_type else None,
        "available_space": shelf.available_space,
        "next_available_position": next_position
    }


@router.get("/barcode/{value}/shelved", response_model=Page[dict])
def get_shelved_entities_by_shelf_barcode_value(
    value: str, session: Session = Depends(get_session)
):
    """
    Retrieve tray and non_tray barcode list from things on a shelf
    using a shelf barcode value
    """
    shelf_statement = select(Shelf).join(Barcode).where(Barcode.value == value)
    shelf = session.execute(shelf_statement).scalars().first()
    if not shelf:
        raise NotFound(detail=f"Shelf with barcode value {value} not found")

    shelf_positions = list(
        session.execute(
            select(ShelfPosition).where(ShelfPosition.shelf_id == shelf.id)
        ).scalars().all()
    )

    position_ids = [p.id for p in shelf_positions]

    trays = {
        t.shelf_position_id: t
        for t in session.execute(
            select(Tray)
            .join(Barcode, Tray.barcode_id == Barcode.id)
            .where(Tray.shelf_position_id.in_(position_ids))
        ).scalars().all()
    }

    non_trays = {
        nt.shelf_position_id: nt
        for nt in session.execute(
            select(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .where(NonTrayItem.shelf_position_id.in_(position_ids))
        ).scalars().all()
    }

    results = []
    for shelf_position in shelf_positions:
        # Direct access — no more lookup table traversal
        position_number = shelf_position.position_number

        if shelf_position.id in trays:
            results.append(
                {
                    "type": "tray",
                    "barcode_value": trays[shelf_position.id].barcode.value,
                    "shelf_position_number": position_number,
                }
            )
        elif shelf_position.id in non_trays:
            results.append(
                {
                    "type": "non_tray",
                    "barcode_value": non_trays[shelf_position.id].barcode.value,
                    "shelf_position_number": position_number,
                }
            )

    return paginate_list(results)


@router.post("/", response_model=ShelfDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def create_shelf(
    shelf_input: ShelfInput, session: Session = Depends(get_session)
) -> Shelf:
    """
    Create a shelf and efficiently bulk-creates its associated shelf positions.
    Also generates location strings for the shelf and positions.
    """
    try:
        audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
        from app.utilities import start_session_with_audit_info
        start_session_with_audit_info(audit_info, session)

        # Handle barcode creation transactionally
        shelf_data = shelf_input.model_dump(exclude={"barcode_value"})
        barcode_value = shelf_input.barcode_value

        if barcode_value and not shelf_data.get("barcode_id"):
            # Check if barcode already exists
            existing_barcode = session.execute(
                select(Barcode).where(Barcode.value == barcode_value)
            ).scalars().first()

            if existing_barcode:
                raise ValidationException(
                    detail=f"Barcode '{barcode_value}' already exists in the system."
                )

            # Look up the 'Shelf' barcode type
            from app.models.barcode_types import BarcodeType
            barcode_type = session.execute(
                select(BarcodeType).where(BarcodeType.name == "Shelf")
            ).scalars().first()

            if not barcode_type:
                raise ValidationException(detail="Barcode type 'Shelf' not found.")

            # Validate against allowed pattern if configured
            if barcode_type.allowed_pattern:
                if not re.fullmatch(barcode_type.allowed_pattern, barcode_value):
                    raise ValidationException(
                        detail=f"Barcode '{barcode_value}' does not match the required pattern for type 'Shelf'."
                    )

            # Create barcode in the same transaction
            new_barcode = Barcode(
                value=barcode_value,
                type_id=barcode_type.id,
                withdrawn=False
            )
            session.add(new_barcode)
            session.flush()  # Flush to get the ID without committing
            shelf_data["barcode_id"] = new_barcode.id

        new_shelf = Shelf(**shelf_data)
        session.add(new_shelf)
        session.flush()
        session.refresh(new_shelf)

        # Location strings are auto-generated via @property

        shelf_type = session.get(ShelfType, new_shelf.shelf_type_id)
        if not shelf_type:
             raise ValidationException(detail=f"ShelfType ID {new_shelf.shelf_type_id} not found.")

        # Create shelf positions with direct position_number
        required_numbers = list(range(1, shelf_type.max_capacity + 1))

        shelf_positions_to_create = [
            ShelfPosition(
                shelf_id=new_shelf.id,
                position_number=position_num,
            )
            for position_num in required_numbers
        ]

        if shelf_positions_to_create:
            session.add_all(shelf_positions_to_create)
            session.flush()

            # Location strings are auto-generated via @property
        
        # Re-calculate available space
        if hasattr(new_shelf, 'calc_available_space'):
            new_shelf.calc_available_space(session=session)
            session.add(new_shelf)
            
        session.commit()
        session.refresh(new_shelf)

        log_audit_event(
            session,
            AuditEventType.ENTITY_CREATED,
            f"Shelf created at {new_shelf.location or 'unknown location'}",
            entity_type="shelves",
            entity_id=new_shelf.id,
        )
        session.commit()

        return new_shelf
    except ValidationException:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        raise ValidationException(detail=f"Database integrity error: {e.orig}")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise InternalServerError(detail=f"{e}")


@router.post("/insert", response_model=ShelfInsertOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def insert_shelf(
    shelf_input: ShelfInput, session: Session = Depends(get_session)
):
    """
    Insert a shelf at a specific shelf_number on a ladder, shifting
    existing shelves at that number and above up by 1.

    Uses descending-order processing to avoid unique constraint violations
    on (ladder_id, shelf_number).
    """
    try:
        audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
        insert_at = shelf_input.shelf_number
        ladder_id = shelf_input.ladder_id

        # 1. Find all shelves on this ladder at or above the insertion point
        shelves_to_shift = (
            session.execute(
                select(Shelf)
                .where(Shelf.ladder_id == ladder_id)
                .where(Shelf.shelf_number >= insert_at)
                .order_by(Shelf.shelf_number.desc())
            )
            .scalars()
            .all()
        )

        shifted_count = len(shelves_to_shift)

        # 2. Shift each shelf down by 1 in descending order.
        # Update both shelf_number and location strings simultaneously to satisfy unique constraints for BOTH columns.
        for shelf in shelves_to_shift:
            shelf.shelf_number += 1
            # Location string is auto-generated via @property
            session.add(shelf)

            # Location string is auto-generated via @property

            # Flush immediately to release the old shelf_number and location string for the next shelf in the loop
            session.flush()

        # 4. Handle barcode creation transactionally (same as create_shelf)
        shelf_data = shelf_input.model_dump(exclude={"barcode_value"})
        barcode_value = shelf_input.barcode_value

        if barcode_value and not shelf_data.get("barcode_id"):
            existing_barcode = session.execute(
                select(Barcode).where(Barcode.value == barcode_value)
            ).scalars().first()

            if existing_barcode:
                raise ValidationException(
                    detail=f"Barcode '{barcode_value}' already exists in the system."
                )

            from app.models.barcode_types import BarcodeType
            barcode_type = session.execute(
                select(BarcodeType).where(BarcodeType.name == "Shelf")
            ).scalars().first()

            if not barcode_type:
                raise ValidationException(detail="Barcode type 'Shelf' not found.")

            if barcode_type.allowed_pattern:
                if not re.fullmatch(barcode_type.allowed_pattern, barcode_value):
                    raise ValidationException(
                        detail=f"Barcode '{barcode_value}' does not match the required pattern for type 'Shelf'."
                    )

            new_barcode = Barcode(
                value=barcode_value,
                type_id=barcode_type.id,
                withdrawn=False
            )
            session.add(new_barcode)
            session.flush()
            shelf_data["barcode_id"] = new_barcode.id

        # Create the new shelf at the now-vacant number
        new_shelf = Shelf(**shelf_data)
        session.add(new_shelf)
        session.flush()
        session.refresh(new_shelf)

        # Location strings are auto-generated via @property

        # Create shelf positions
        shelf_type = session.get(ShelfType, new_shelf.shelf_type_id)
        if not shelf_type:
            raise InternalServerError(detail=f"ShelfType ID {new_shelf.shelf_type_id} not found.")

        required_numbers = list(range(1, shelf_type.max_capacity + 1))
        shelf_positions_to_create = [
            ShelfPosition(
                shelf_id=new_shelf.id,
                position_number=position_num,
            )
            for position_num in required_numbers
        ]

        if shelf_positions_to_create:
            session.add_all(shelf_positions_to_create)
            session.flush()

            # Location strings are auto-generated via @property

        # Re-calculate available space
        if hasattr(new_shelf, 'calc_available_space'):
            new_shelf.calc_available_space(session=session)
            session.add(new_shelf)

        # 5. Commit entire transaction
        session.commit()
        session.refresh(new_shelf)

        LOGGER.info(
            f"Inserted shelf at position {insert_at} on ladder {ladder_id}. "
            f"Shifted {shifted_count} existing shelves."
        )

        return {"shelf": new_shelf, "shifted_count": shifted_count}

    except IntegrityError as e:
        session.rollback()
        raise ValidationException(detail=f"Integrity error during insert-and-shift: {e.orig}")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise InternalServerError(detail=f"Insert-and-shift failed: {e}")


@router.patch("/bulk", response_model=List[ShelfDetailWriteOutput], dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def bulk_update_shelves(
    updates: List[ShelfBulkUpdateInput],
    session: Session = Depends(get_session),
):
    """
    Bulk update shelves. Each item must include an 'id' field.
    If shelf_type_id is changed, shelf positions are adjusted to match
    the new max_capacity (same logic as single-shelf update).
    """
    results = []
    for update in updates:
        data = update.model_dump(exclude_unset=True)
        shelf_id = data.pop("id")

        shelf = session.get(Shelf, shelf_id)
        if not shelf:
            raise NotFound(detail=f"Shelf ID {shelf_id} Not Found")

        # Adjust positions when shelf_type changes
        if "shelf_type_id" in data and data["shelf_type_id"] != shelf.shelf_type_id:
            _adjust_shelf_positions(session, shelf_id, shelf.shelf_type_id, data["shelf_type_id"])

        for key, value in data.items():
            setattr(shelf, key, value)

        setattr(shelf, "update_dt", datetime.now(timezone.utc))
        session.add(shelf)
        session.flush()  # flush each shelf so position changes are visible

        # Re-calculate available space
        if hasattr(shelf, 'calc_available_space'):
            shelf.calc_available_space(session=session)
            session.add(shelf)

        results.append(shelf)

    session.commit()
    for r in results:
        session.refresh(r)

    for r in results:
        log_audit_event(
            session,
            AuditEventType.ENTITY_UPDATED,
            f"Shelf {r.id} bulk updated",
            entity_type="shelves",
            entity_id=r.id,
        )
    session.commit()

    return results


@router.patch("/{id}", response_model=ShelfDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def update_shelf(
    id: int, shelf_input: ShelfUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a shelf with the given ID.
    If the shelf_type is changed, this will adjust the number of shelf positions
    to match the new max_capacity, but only if the positions being removed are empty.
    """
    existing_shelf = session.get(Shelf, id)

    if existing_shelf is None:
        raise NotFound(detail=f"Shelf ID {id} Not Found")

    mutated_data = shelf_input.model_dump(exclude_unset=True)

    # Handle barcode_value transactionally (same pattern as create_shelf)
    barcode_value = mutated_data.pop("barcode_value", None)
    
    if barcode_value:
        existing_barcode = session.execute(
            select(Barcode).where(Barcode.value == barcode_value)
        ).scalars().first()

        # Only throw an error if the barcode exists AND it belongs to a different entity
        if existing_barcode and existing_shelf.barcode_id != existing_barcode.id:
            raise ValidationException(
                detail=f"Barcode '{barcode_value}' already exists in the system."
            )
            
        # If there's no barcode_id provided but we have a text value to create, create a new one
        if not mutated_data.get("barcode_id") and not existing_barcode:
            from app.models.barcode_types import BarcodeType
            barcode_type = session.execute(
                select(BarcodeType).where(BarcodeType.name == "Shelf")
            ).scalars().first()

            if not barcode_type:
                raise ValidationException(detail="Barcode type 'Shelf' not found.")

            if barcode_type.allowed_pattern:
                if not re.fullmatch(barcode_type.allowed_pattern, barcode_value):
                    raise ValidationException(
                        detail=f"Barcode '{barcode_value}' does not match the required pattern for type 'Shelf'."
                    )

            new_barcode = Barcode(
                value=barcode_value,
                type_id=barcode_type.id,
                withdrawn=False
            )
            session.add(new_barcode)
            session.flush()
            mutated_data["barcode_id"] = new_barcode.id

    # --- LOGIC TO HANDLE SHELF CAPACITY CHANGES ---
    if "shelf_type_id" in mutated_data and mutated_data["shelf_type_id"] != existing_shelf.shelf_type_id:
        _adjust_shelf_positions(session, id, existing_shelf.shelf_type_id, mutated_data["shelf_type_id"])

    # Apply all other attribute changes
    for key, value in mutated_data.items():
        setattr(existing_shelf, key, value)

    setattr(existing_shelf, "update_dt", datetime.now(timezone.utc))
    session.add(existing_shelf)
    session.flush()

    # Re-calculate available space
    if hasattr(existing_shelf, 'calc_available_space'):
        existing_shelf.calc_available_space(session=session)
        session.add(existing_shelf)
        
    session.commit()
    session.refresh(existing_shelf)

    log_audit_event(
        session,
        AuditEventType.ENTITY_UPDATED,
        f"Shelf {id} updated",
        entity_type="shelves",
        entity_id=id,
    )
    session.commit()

    return existing_shelf


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def delete_shelf(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelf by its ID.
    """
    shelf = session.get(Shelf, id)

    if shelf:
        # Check for items on this shelf
        # V2: Use select(func.count()) for efficiency
        items_count_query = (
            select(func.count(ShelfPosition.id))
            .where(ShelfPosition.shelf_id == id)
            .where(
                (ShelfPosition.tray != None) | (ShelfPosition.non_tray_item != None)
            )
        )
        items_count = session.execute(items_count_query).scalar()

        if items_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete Shelf {shelf.shelf_number}: {items_count} items are shelved on it."
            )

        log_audit_event(
            session,
            AuditEventType.ENTITY_DELETED,
            f"Shelf {id} deleted",
            entity_type="shelves",
            entity_id=id,
        )
        session.delete(shelf)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Shelf ID {id} Not Found")


# NOTE: /bulk must be registered BEFORE /{id} to avoid FastAPI route shadowing.
# It has been moved here; the original was at the end of the file.