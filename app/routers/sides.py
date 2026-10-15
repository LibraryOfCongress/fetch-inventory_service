# /code/app/routers/sides.py - REFACRORED TO SQLALCHEMY V2

from typing import Optional

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams, SideFilterParams
from app.models.sides import Side
from app.models.side_orientations import SideOrientation
from app.models.buildings import Building
from app.models.aisles import Aisle
from app.models.modules import Module
from app.schemas.sides import (
    SideInput,
    SideUpdateInput,
    SideListOutput,
    SideDetailWriteOutput,
    SideDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/sides",
    tags=["sides"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/", response_model=Page[SideListOutput])
def get_side_list(
    session: Session = Depends(get_session),
    params: SideFilterParams = Depends(),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None),
) -> list:
    """
    Get a paginated list of sides from the database.
    """
    # Create a query to select all sides from the database
    query = (
        select(Side)
        .join(Aisle, Side.aisle_id == Aisle.id)
        .join(Module, Module.id == Aisle.module_id)
        .join(Building, Building.id == Module.building_id)
    )

    if search:
        query = query.join(
            SideOrientation, Side.side_orientation_id == SideOrientation.id
        ).where(SideOrientation.name.icontains(search))

    if params.aisle_id:
        query = query.where(Aisle.id == params.aisle_id)
    if params.module_id:
        query = query.where(Module.id == params.module_id)
    if params.building_id:
        query = query.where(Building.id == params.building_id)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(Side)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=SideDetailReadOutput)
def get_side_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a side by its ID.
    """
    side = session.get(Side, id)

    if side:
        return side

    raise NotFound(detail=f"Side ID {id} Not Found")


@router.post("/", response_model=SideDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def create_side(side_input: SideInput, session: Session = Depends(get_session)):
    """
    Create a new side record.
    """
    try:
        # Create a new side
        new_side = Side(**side_input.model_dump())
        session.add(new_side)
        session.commit()
        session.refresh(new_side)

        return new_side

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=SideDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def update_side(
    id: int, side: SideUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a side record in the database.
    """
    try:
        # Get the existing side record from the database
        existing_side = session.get(Side, id)

        # Check if the side record exists
        if not existing_side:
            raise NotFound(detail=f"Side ID {id} Not Found")

        # Update the side record with the mutated data
        mutated_data = side.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_side, key, value)
        setattr(existing_side, "update_dt", datetime.now(timezone.utc))

        # Commit the changes to the database
        session.add(existing_side)
        session.commit()
        session.refresh(existing_side)

        return existing_side

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def delete_side(id: int, session: Session = Depends(get_session)):
    """
    Delete a side by its ID.
    """
    side = session.get(Side, id)

    if side:
        session.delete(side)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Side ID {id} Not Found")
