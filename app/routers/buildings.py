from datetime import datetime, timezone
from typing import Optional

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate 
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, func     # select is imported from sqlalchemy now
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.buildings import Building
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.ladders import Ladder
from app.models.shelves import Shelf
from app.models.shelf_positions import ShelfPosition
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.schemas.buildings import (
    BuildingInput,
    BuildingUpdateInput,
    BuildingListOutput,
    BuildingDetailWriteOutput,
    BuildingDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter

# For future circular imports
# https://sqlmodel.tiangolo.com/tutorial/code-structure/#import-only-while-editing-with-type_checking

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/buildings",
    tags=["buildings"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/", response_model=Page[BuildingListOutput])
def get_building_list(
    # NOTE: Session type hint is from sqlalchemy.orm
    session: Session = Depends(get_session), 
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Building name"),
) -> list:
    """
    Get a paginated list of buildings.
    """
    # Create a query to retrieve all Building
    query = select(Building)

    if search:
        # NOTE: SQLAlchemy V2 encourages func.lower() for case-insensitive search if your dialect requires it
        query = query.where(Building.name.icontains(search))

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using RequestSorter
        sorter = BaseSorter(Building)
        # Assuming sorter.apply_sorting handles SQLAlchemy's Selectable query objects
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=BuildingDetailReadOutput)
def get_building_detail(id: int, session: Session = Depends(get_session)):
    """
    Get building detail by ID.
    """
    # session.get() is compatible with SQLAlchemy V2
    building = session.get(Building, id) 
    if building:
        return building

    raise NotFound(detail=f"Building ID {id} Not Found")


@router.post("/", response_model=BuildingDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def create_building(
    building_input: BuildingInput, session: Session = Depends(get_session)
) -> Building:
    """
    Create a building:
    """
    try:
        # model_dump() is a Pydantic V2 feature (correctly used here)
        new_building = Building(**building_input.model_dump()) 
        session.add(new_building)
        session.commit()
        session.refresh(new_building)
        return new_building

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=BuildingDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def update_building(
    id: int, building: BuildingUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a building:
    """
    try:
        existing_building = session.get(Building, id)

        if existing_building is None:
            raise NotFound(detail=f"Building ID {id} Not Found")

        mutated_data = building.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_building, key, value)

        setattr(existing_building, "update_dt", datetime.now(timezone.utc))

        session.add(existing_building)
        session.commit()
        session.refresh(existing_building)

        return existing_building

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_manage_locations"))])
def delete_building(id: int, session: Session = Depends(get_session)):
    """
    Delete a building by ID.
    """

    building = session.get(Building, id)

    if building:
        # Check for items on any shelf in this building
        items_count_query = (
            select(func.count(ShelfPosition.id))
            .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
            .join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .join(Module, Aisle.module_id == Module.id)
            .where(Module.building_id == id)
            .where(
                (ShelfPosition.tray != None) | (ShelfPosition.non_tray_item != None)
            )
        )
        items_count = session.execute(items_count_query).scalar()

        if items_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete Building {building.name}: {items_count} items are shelved in its modules."
            )

        session.delete(building)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Building ID {id} Not Found")