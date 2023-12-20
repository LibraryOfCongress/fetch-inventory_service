from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.sides import Side
from app.schemas.sides import (
    SideInput,
    SideListOutput,
    SideDetailWriteOutput,
    SideDetailReadOutput,
)


router = APIRouter(
    prefix="/sides",
    tags=["sides"],
)


@router.get("/", response_model=Page[SideListOutput])
def get_side_list(session: Session = Depends(get_session)) -> list:
    """
    Get a paginated list of sides from the database.

    **Returns**:
    - list: A paginated list of sides.
    """
    # Create a query to select all sides from the database
    return paginate(session, select(Side))


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
    else:
        raise HTTPException(status_code=404, detail="Not Found")


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

    # Create a new side
    new_side = Side(**side_input.model_dump())
    session.add(new_side)
    session.commit()
    session.refresh(new_side)
    return new_side


@router.patch("/{id}", response_model=SideDetailWriteOutput)
def update_side(id: int, side: SideInput, session: Session = Depends(get_session)):
    """
    Update a side record in the database.

    **Parameters**:
    - id: The ID of the side record to update.
    - Side Input: The updated side data.

    **Returns**:
    - Side Detail Write Output: The updated side record.
    """
    # Get the existing side record from the database
    existing_side = session.get(Side, id)

    # Check if the side record exists
    if not existing_side:
        raise HTTPException(status_code=404, detail="Not Found")

    # Update the side record with the mutated data
    mutated_data = side.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_side, key, value)
    setattr(existing_side, "update_dt", datetime.utcnow())

    # Commit the changes to the database
    session.add(existing_side)
    session.commit()
    session.refresh(existing_side)

    return existing_side


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
        return HTTPException(status_code=204)
    else:
        raise HTTPException(status_code=404)
