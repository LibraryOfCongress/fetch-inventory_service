# /code/app/routers/aisles.py - REFACTORED: Removed AisleNumber lookup table dependency

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from typing import Optional

from app.database.session import get_session
from app.filter_params import SortParams, AisleFilterParams
from app.models.aisles import Aisle
from app.models.modules import Module
from app.models.sides import Side
from app.models.ladders import Ladder
from app.models.shelves import Shelf
from app.models.shelf_positions import ShelfPosition
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.schemas.aisles import (
    AisleInput,
    AisleUpdateInput,
    AisleListOutput,
    AisleDetailWriteOutput,
    AisleDetailReadOutput,
)
from app.config.exceptions import NotFound, ValidationException, InternalServerError

import traceback

from app.sorting import BaseSorter, AisleSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/aisles",
    tags=["aisles"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/", response_model=Page[AisleListOutput])
def get_aisle_list(
    session: Session = Depends(get_session),
    params: AisleFilterParams = Depends(),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Aisle Number"),
) -> list:
    """
    Get a paginated list of aisles.
    """
    query = select(Aisle).join(Module, Aisle.module_id == Module.id)

    if search:
        query = query.where(Aisle.aisle_number == int(search))

    if params.module_number:
        query = query.where(Module.module_number == params.module_number)

    if params.building_id:
        query.where(Module.building_id == params.building_id)

    if params.module_id:
        query = query.where(Module.id == params.module_id)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = AisleSorter(Aisle)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=AisleDetailReadOutput)
def get_aisle_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of an aisle from the database using the provided ID.
    """
    aisle = session.get(Aisle, id)

    if aisle:
        return aisle

    raise NotFound(detail=f"Aisle ID {id} Not Found")


@router.post("/", response_model=AisleDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def create_aisle(aisle_input: AisleInput, session: Session = Depends(get_session)):
    """
    Create a new aisle.
    """
    try:
        new_aisle = Aisle(**aisle_input.model_dump())
        session.add(new_aisle)
        session.commit()
        session.refresh(new_aisle)

        return new_aisle

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=AisleDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def update_aisle(
    id: int, aisle: AisleUpdateInput, session: Session = Depends(get_session)
):
    """
    Updates an aisle with the given ID using the provided aisle data.
    """
    try:
        existing_aisle = session.get(Aisle, id)

        if not existing_aisle:
            raise NotFound(detail=f"Aisle ID {id} Not Found")

        mutated_data = aisle.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_aisle, key, value)

        setattr(existing_aisle, "update_dt", datetime.now(timezone.utc))

        session.add(existing_aisle)
        session.commit()
        session.refresh(existing_aisle)

        return existing_aisle

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def delete_aisle(id: int, session: Session = Depends(get_session)):
    """
    Delete an aisle with the given id.
    """
    aisle = session.get(Aisle, id)

    if aisle:
        # Check for items on any shelf in this aisle
        items_count_query = (
            select(func.count(ShelfPosition.id))
            .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
            .join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .where(Side.aisle_id == id)
            .where(
                (ShelfPosition.tray != None) | (ShelfPosition.non_tray_item != None)
            )
        )
        items_count = session.execute(items_count_query).scalar()

        if items_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete Aisle {aisle.aisle_number}: {items_count} items are shelved in its side(s)."
            )

        session.delete(aisle)
        session.commit()
        return Response(status_code=204)

    raise NotFound(detail=f"Aisle ID {id} Not Found")