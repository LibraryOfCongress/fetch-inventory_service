from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams, SideFilterParams
from app.models.sides import Side
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

router = APIRouter(
    prefix="/sides",
    tags=["sides"],
)


@router.get("/", response_model=Page[SideListOutput])
def get_side_list(
    session: Session = Depends(get_session),
    params: SideFilterParams = Depends(),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a paginated list of sides from the database.

    **Parameters:**
    - sort_params: The sorting parameters.

    **Returns**:
    - Side List Output: A paginated list of sides.
    """
    # Create a query to select all sides from the database
    query = select(Side).join(
        Aisle, Side.aisle_id == Aisle.id
    ).join(
        Module, Module.id == Aisle.module_id
    ).join(
        Building, Building.id == Module.building_id
    )

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

    **Args**:
    - id: The ID of the side.

    **Returns**:
    - Side Detail Read Output: The details of the side.

    **Raises**:
    - HTTPException: If the side is not found.
    """
    side = session.get(Side, id)

    if side:
        return side

    raise NotFound(detail=f"Side ID {id} Not Found")


@router.post("/", response_model=SideDetailWriteOutput, status_code=201)
def create_side(side_input: SideInput, session: Session = Depends(get_session)):
    """
    Create a new side record.

    **Parameters**:
    - Side Input: The input data for the new side.

    **Returns**:
    - Side Detail Write Output: The newly created side record.

    **Notes**:
    - **aisle_id**: Required integer id for an aisle the side belongs to.
    - **side_orientation_id**: Required integer id for orientation

    **Constraints**:
    - Aisle and Side Orientation form a unique together constraint. For example, there
    cannot exist two left sides within one aisle.
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


@router.patch("/{id}", response_model=SideDetailWriteOutput)
def update_side(
    id: int, side: SideUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a side record in the database.

    **Parameters**:
    - id: The ID of the side record to update.
    - Side Update Input: The updated side data.

    **Returns**:
    - Side Detail Write Output: The updated side record.
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

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_side(id: int, session: Session = Depends(get_session)):
    """
    Delete a side by its ID.

    **Parameters**:
    - id: The ID of the side to delete.

    **Returns**:
    - Response: A 204 No Content response if the side is deleted successfully.

    **Raises**:
    - HTTPException: If the side ID is missing or not an integer, or if the side is
    not found.
    """
    side = session.get(Side, id)

    if side:
        session.delete(side)
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Side id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Side ID {id} Not Found")
