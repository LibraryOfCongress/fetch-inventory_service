from typing import Sequence

from fastapi import APIRouter, HTTPException, Depends, Response
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


@router.get("/", response_model=list[SideListOutput])
def get_side_list(session: Session = Depends(get_session)) -> list:
    """
    Get a list of all sides.
    Parameters:
    Returns:
        - A list of SideListOutput objects representing the sides.
    """
    # Create a query to select all sides from the database
    query = select(Side)

    try:
        # Execute the query using the session and retrieve all results
        results = session.exec(query)

        return results.all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.get("/{id}", response_model=SideDetailReadOutput)
def get_side_detail(id: int, session: Session = Depends(get_session)):
    """
    Get side detail by id.
    Parameters:
        - id (int): The id of the side.
    Returns:
        - SideDetailReadOutput: The side detail.
    Raises:
        - HTTPException: If the side id is invalid or not found.
    """
    if not id or not isinstance(id, int):
        raise HTTPException(status_code=404, detail="Side ID is required")

    try:
        side = session.get(Side, id)
        if side:
            return side
        else:
            raise HTTPException(status_code=404, detail="Side not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.post("/", response_model=SideDetailWriteOutput, status_code=201)
def create_side(side_input: SideInput, session: Session = Depends(get_session)):
    """
    Create a side:

    - **aisle_id**: Required integer id for an aisle the side belongs to.
    - **side_orientation_id**: Required integer id for orientation
    - **barcode**: Optional uuid for related barcode

    Constraints:

    Aisle and Side Orientation form a unique together constraint. For example, there cannot exist two left sides within one aisle.
   """
    # Check if side_input is empty
    if not side_input:
        raise HTTPException(status_code=400, detail="Side data is required")

    # Create a new side
    new_side = Side(**side_input.model_dump())

    try:
        session.add(new_side)
        session.commit()
        session.refresh(new_side)

        return new_side
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.patch("/{id}", response_model=SideDetailWriteOutput)
def update_side(id: int, side: SideInput, session: Session = Depends(get_session)):
    """
    Update a side record in the database.
    Parameters:
       - id (int): The ID of the side record to update.
       - side (SideInput): The updated side data.
    Returns:
       - SideDetailWriteOutput: The updated side record.
        """
    # Check if id is provided and is an integer
    if not id or not isinstance(id, int):
        raise HTTPException(status_code=404, detail="Side ID is required")

    try:
        # Get the existing side record from the database
        existing_side = session.get(Side, id)

        # Check if the side record exists
        if not existing_side:
            raise HTTPException(status_code=404, detail="Side not found")

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_side(id: int, session: Session = Depends(get_session)):
    """
    Delete a side by its ID.

    Parameters:
       - id (int): The ID of the side to delete.

    Raises:
       - HTTPException: If the side ID is missing or not an integer, or if the side is not found.

    Returns:
       - Response: A 204 No Content response if the side is deleted successfully.
    """
    if not id or not isinstance(id, int):
        raise HTTPException(status_code=404, detail="Side ID is required")

    side = session.get(Side, id)

    try:
        if side:
            session.delete(side)
            session.commit()

            return Response(status_code=204, content={"detail": f"Side {id} deleted successfully"})
        else:
            raise HTTPException(status_code=404, detail="Side not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")