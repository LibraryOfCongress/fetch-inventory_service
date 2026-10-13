# /code/app/routers/shelf_types.py - FULLY REFACRORED TO SQLALCHEMY V2

import logging
from typing import Optional, List

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, func, update # select/update/func imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

# --- START: MODIFIED/NEW IMPORTS FOR BACKGROUND TASK ---
from app.database.session import get_session, AppSessionLocal # AppSessionLocal is a synchronous session factory
from app.filter_params import SortParams
from app.models.shelf_types import ShelfType
from app.models.shelves import Shelf
from app.models.size_class import SizeClass
from app.models.shelf_positions import ShelfPosition
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
# --- END: MODIFIED/NEW IMPORTS FOR BACKGROUND TASK ---

from app.schemas.shelf_types import (
    ShelfTypeInput,
    ShelfTypeUpdateInput,
    ShelfTypeListOutput,
    ShelfTypeDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    MethodNotAllowed,
    ValidationException,
    InternalServerError,
    BadRequest,
)
from app.sorting import BaseSorter

# --- START: NEW LOGGER ---
LOGGER = logging.getLogger(__name__)
# --- END: NEW LOGGER ---

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/shelf-types",
    tags=["shelf types"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


# ======================================================================
# ========= START: NEW BACKGROUND TASK FUNCTION (V2 CONVERTED) =========
# ======================================================================
def resize_shelves_for_type(
    shelf_type_id: int,
    old_capacity: int,
    new_capacity: int,
):
    """
    A background task to resize all shelves of a given type.
    It creates its own database session to ensure it works after the initial request is closed.
    CRITICAL: All session.exec() calls are converted to V2 execution.
    """
    # Create a new, independent database session for this task.
    session = AppSessionLocal()
    LOGGER.info(f"Background Task: Starting resize for ShelfType ID {shelf_type_id}.")
    try:
        # Find all shelves that use this shelf type.
        # V2 FIX: session.exec().all() -> session.execute(select(...)).scalars().all()
        affected_shelves = session.execute(select(Shelf).where(Shelf.shelf_type_id == shelf_type_id)).scalars().all()
        if not affected_shelves:
            LOGGER.info("Background Task: No shelves found for this type. Task finished.")
            return

        # Handle capacity changes
        if new_capacity < old_capacity:
            # --- DECREASING CAPACITY ---
            num_to_remove = old_capacity - new_capacity
            for shelf in affected_shelves:
                # Find the positions with the highest numbers to remove them.
                positions_to_check_query = (
                    select(ShelfPosition)
                    .where(ShelfPosition.shelf_id == shelf.id)
                    .order_by(ShelfPosition.position_number.desc())
                    .limit(num_to_remove)
                )
                # V2 FIX: session.exec().all() -> session.execute(select(...)).scalars().all()
                positions_to_delete = session.execute(positions_to_check_query).scalars().all()
                position_ids_to_delete = [p.id for p in positions_to_delete]

                if not position_ids_to_delete:
                    continue

                # SAFETY CHECK: Ensure these positions are empty.
                # V2 FIX: session.exec().first() -> session.execute(select(...)).first()
                occupied_tray = session.execute(select(Tray.id).where(Tray.shelf_position_id.in_(position_ids_to_delete)).limit(1)).first()
                occupied_non_tray = session.execute(select(NonTrayItem.id).where(NonTrayItem.shelf_position_id.in_(position_ids_to_delete)).limit(1)).first()

                if occupied_tray or occupied_non_tray:
                    LOGGER.warning(f"Background Task: Cannot resize Shelf ID {shelf.id}: positions are occupied. Skipping.")
                    continue

                # If safe, delete the positions.
                for pos in positions_to_delete:
                    session.delete(pos)
                LOGGER.info(f"Background Task: Successfully removed {len(positions_to_delete)} positions from Shelf ID {shelf.id}.")

        elif new_capacity > old_capacity:
            # --- INCREASING CAPACITY ---
            new_position_numbers_range = list(range(old_capacity + 1, new_capacity + 1))
            if new_position_numbers_range:
                # Direct position_number — no lookup table needed
                for shelf in affected_shelves:
                    for position_num in new_position_numbers_range:
                        new_position = ShelfPosition(shelf_id=shelf.id, position_number=position_num)
                        session.add(new_position)
                    LOGGER.info(f"Background Task: Queued {len(new_position_numbers_range)} new positions for Shelf ID {shelf.id}.")

        session.commit()
        
        # Recalculate available space after committing the resize.
        for shelf in affected_shelves:
            if hasattr(shelf, 'calc_available_space'):
                # NOTE: calc_available_space is a method on the ORM object that needs the session for its V2 internal queries
                shelf.calc_available_space(session=session)
                session.add(shelf)
        session.commit()
        
    finally:
        # CRITICAL: Always close the session when the task is done.
        session.close()
        LOGGER.info(f"Background Task: Finished for ShelfType ID {shelf_type_id}. Session closed.")
# ======================================================================
# ========= END: NEW BACKGROUND TASK FUNCTION (V2 CONVERTED) ============
# ======================================================================


@router.get("/", response_model=Page[ShelfTypeListOutput])
def get_shelf_type_list(
    session: Session = Depends(get_session),
    size_class_id: int = None,
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Shelf Type Type"),
) -> list:
    query = select(ShelfType)
    if search:
        query = query.where(ShelfType.type.icontains(search))
    if size_class_id:
        query = query.where(ShelfType.size_class_id == size_class_id)
    if sort_params.sort_by:
        sorter = BaseSorter(ShelfType)
        query = sorter.apply_sorting(query, sort_params)
    return paginate(session, query)


@router.get("/{id}", response_model=ShelfTypeDetailOutput)
def get_shelf_type_detail(id: int, session: Session = Depends(get_session)):
    if not id:
        raise BadRequest(detail="Shelf Type ID Required")
    shelf_type = session.get(ShelfType, id)
    if shelf_type:
        return shelf_type
    raise NotFound(detail=f"Shelf Type ID {id} Not Found")


@router.post("/", response_model=ShelfTypeDetailOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def create_shelf_type(
    shelf_type_input: ShelfTypeInput, session: Session = Depends(get_session)
):
    try:
        new_shelf_type = ShelfType(**shelf_type_input.model_dump())
        session.add(new_shelf_type)
        session.commit()
        session.refresh(new_shelf_type)
        return new_shelf_type
    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


# --- START: COMPLETELY REVISED `update_shelf_type` FUNCTION ---
@router.patch("/{id}", response_model=ShelfTypeDetailOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def update_shelf_type(
    id: int,
    shelf_type_input: ShelfTypeUpdateInput,
    background_tasks: BackgroundTasks, # This dependency is new
    session: Session = Depends(get_session),
):
    """
    Update an existing Shelf Type. If max_capacity is changed, a background
    task is triggered to resize all associated shelves.
    """
    existing_shelf_type = session.get(ShelfType, id)
    if not existing_shelf_type:
        raise NotFound(detail=f"Shelf Type ID {id} not found")

    # Store the old capacity before we make any changes.
    old_capacity = existing_shelf_type.max_capacity

    # Update the shelf type record with the new data.
    mutated_data = shelf_type_input.model_dump(exclude_unset=True)
    for key, value in mutated_data.items():
        setattr(existing_shelf_type, key, value)
    
    setattr(existing_shelf_type, "update_dt", datetime.now(timezone.utc))
    session.add(existing_shelf_type)
    session.commit()
    session.refresh(existing_shelf_type)

    # Check if the capacity has actually changed.
    new_capacity = existing_shelf_type.max_capacity
    if new_capacity != old_capacity:
        LOGGER.info(f"API: ShelfType ID {id} capacity changed from {old_capacity} to {new_capacity}. Scheduling background task.")
        # If it has changed, add the resizing function to run in the background.
        background_tasks.add_task(
            resize_shelves_for_type,
            id,
            old_capacity,
            new_capacity
        )

    return existing_shelf_type
# --- END: COMPLETELY REVISED `update_shelf_type` FUNCTION ---


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def delete_shelf_type(id: int, session: Session = Depends(get_session)):
    if not id:
        raise BadRequest(detail="Shelf Type ID Required")
    shelf_type = session.get(ShelfType, id)
    if shelf_type:
        # V2 FIX: session.exec().one() -> session.execute(select(...)).scalar_one()
        child_shelves_count = session.execute(
            select(func.count(Shelf.id)).where(Shelf.shelf_type_id == id)
        ).scalar_one()
        if child_shelves_count > 0:
            # V2 FIX: session.exec().one_or_none() -> session.execute(select(...)).scalars().one_or_none()
            shelf_type_size_class = session.execute(
                select(SizeClass).where(SizeClass.id == shelf_type.size_class_id)
            ).scalars().one_or_none()
            raise MethodNotAllowed(
                detail=f"""Cannot delete Shelf Type id {id} ({shelf_type_size_class.short_name} {shelf_type.type}), it is in use by {child_shelves_count} shelves"""
            )
        else:
            session.delete(shelf_type)
            session.commit()
        return Response(status_code=204)
    raise NotFound(detail=f"Shelf Type ID {id} Not Found")
