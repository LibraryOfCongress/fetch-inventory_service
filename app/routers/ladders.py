# /code/app/routers/ladders.py - REFACTORED: Removed LadderNumber lookup table dependency

from typing import Optional, List

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams, LadderFilterParams
from app.models.buildings import Building
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.ladders import Ladder
from app.models.shelves import Shelf
from app.models.shelf_positions import ShelfPosition
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.schemas.ladders import (
    LadderInput,
    LadderUpdateInput,
    LadderBulkUpdateInput,
    LadderListOutput,
    LadderDetailWriteOutput,
    LadderDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter, LadderSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/ladders",
    tags=["ladders"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/", response_model=Page[LadderListOutput])
def get_ladder_list(
    session: Session = Depends(get_session),
    params: LadderFilterParams = Depends(),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Ladder Number"),
) -> list:
    """
    Retrieve a paginated list of ladders.
    """

    query = (
        select(Ladder)
        .join(Side, Ladder.side_id == Side.id)
        .join(Aisle, Side.aisle_id == Aisle.id)
        .join(Module, Aisle.module_id == Module.id)
        .join(Building, Module.building_id == Building.id)
    )

    if search:
        query = query.where(Ladder.ladder_number == int(search))

    if params.building_id:
        query = query.where(Building.id == params.building_id)
    if params.module_id:
        query = query.where(Module.id == params.module_id)
    if params.aisle_id:
        query = query.where(Aisle.id == params.aisle_id)
    if params.side_id:
        query = query.where(Side.id == params.side_id)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = LadderSorter(Ladder)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=LadderDetailReadOutput)
def get_ladder_detail(
    id: int,
    session: Session = Depends(get_session),
):
    """
    Retrieve the details of a ladder by its ID.
    """
    try:
        ladder = session.get(Ladder, id)

        if not ladder:
            raise NotFound(detail=f"Ladder ID {id} Not Found")
        return ladder

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")
    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.post("/", response_model=LadderDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def create_ladder(
    ladder_input: LadderInput, session: Session = Depends(get_session)
) -> Ladder:
    """
    Create a ladder.
    """
    try:
        new_ladder = Ladder(**ladder_input.model_dump())
        session.add(new_ladder)
        session.commit()
        session.refresh(new_ladder)

        return new_ladder

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=LadderDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def update_ladder(
    id: int, ladder: LadderUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a ladder with the given ID.
    """

    try:
        existing_ladder = session.get(Ladder, id)

        if not existing_ladder:
            raise NotFound(detail=f"Ladder ID {id} Not Found")

        mutated_data = ladder.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_ladder, key, value)

        setattr(existing_ladder, "update_dt", datetime.now(timezone.utc))

        session.add(existing_ladder)
        session.commit()
        session.refresh(existing_ladder)

        return existing_ladder

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def delete_ladder(id: int, session: Session = Depends(get_session)):
    """
    Delete a ladder with the given ID.
    """
    ladder = session.get(Ladder, id)

    if ladder:
        # Check for items on any shelf belonging to this ladder
        items_count_query = (
            select(func.count(ShelfPosition.id))
            .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
            .where(Shelf.ladder_id == id)
            .where(
                (ShelfPosition.tray != None) | (ShelfPosition.non_tray_item != None)
            )
        )
        items_count = session.execute(items_count_query).scalar()

        if items_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete Ladder {ladder.ladder_number}: {items_count} items are shelved on its shelves."
            )

        session.delete(ladder)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Ladder ID {id} Not Found")


@router.patch("/bulk", response_model=List[LadderDetailWriteOutput], dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def bulk_update_ladders(
    updates: List[LadderBulkUpdateInput],
    session: Session = Depends(get_session),
):
    """
    Bulk update ladders. Each item must include an 'id' field.
    Designed for batch-editing sort_priority.
    """
    results = []
    for update in updates:
        data = update.model_dump(exclude_unset=True)
        ladder_id = data.pop("id")

        ladder = session.get(Ladder, ladder_id)
        if not ladder:
            raise NotFound(detail=f"Ladder ID {ladder_id} Not Found")

        for key, value in data.items():
            setattr(ladder, key, value)

        setattr(ladder, "update_dt", datetime.now(timezone.utc))
        session.add(ladder)
        results.append(ladder)

    session.commit()
    for r in results:
        session.refresh(r)

    return results
