from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.buildings import Building
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

router = APIRouter(
    prefix="/buildings",
    tags=["buildings"],
)


@router.get("/", response_model=Page[BuildingListOutput])
def get_building_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Building name"),
) -> list:
    """
    Get a paginated list of buildings.

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.
    - search (Optional[str]): The search query.
        - Name: The name of the building to search for.

    **Returns:**
    - Building List Output: The paginated list of buildings.
    """
    # Create a query to retrieve all Building
    query = select(Building)

    if search:
        query = query.where(Building.name.icontains(search))

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using RequestSorter
        sorter = BaseSorter(Building)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=BuildingDetailReadOutput)
def get_building_detail(id: int, session: Session = Depends(get_session)):
    """
    Get building detail by ID.

    **Args:**
    - id: The ID of the building.

    **Returns:**
    - Building Detail Read Output: The building detail.

    **Raises:**
    - HTTPException: If the building is not found.
    """

    building = session.get(Building, id)
    if building:
        return building

    raise NotFound(detail=f"Building ID {id} Not Found")


@router.post("/", response_model=BuildingDetailWriteOutput, status_code=201)
def create_building(
    building_input: BuildingInput, session: Session = Depends(get_session)
) -> Building:
    """
    Create a building:

    **Args:**
    - Building Input: The input data for creating the building.

    **Returns:**
    - Building Detail Write Output: The newly created building.
    """
    try:
        new_building = Building(**building_input.model_dump())
        session.add(new_building)
        session.commit()
        session.refresh(new_building)
        return new_building

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=BuildingDetailWriteOutput)
def update_building(
    id: int, building: BuildingUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a building:

    **Args:**
    - id (int): The ID of the building to update.
    - Building Update Input: The updated building data.

    **Returns:**
    - Building Detail Write Output: The updated building.

    **Raises:**
    - HTTPException: If the building with the given ID is not found or if there is an
    internal server error.
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

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_building(id: int, session: Session = Depends(get_session)):
    """
    Delete a building by ID.

    **Args:**
    - id: The ID of the building to delete.

    **Returns:**
    - None

    **Raises:**
    - HTTPException: If the building with the specified ID is not found.
    """

    building = session.get(Building, id)

    if building:
        session.delete(building)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Building ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Building ID {id} Not Found")
