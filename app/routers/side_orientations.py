from typing import Sequence

from fastapi import APIRouter, HTTPException, Depends, Response
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.side_orientations import SideOrientation

from app.schemas.side_orientations import (
    SideOrientationInput,
    SideOrientationListOutput,
    SideOrientationDetailWriteOutput,
    SideOrientationDetailReadOutput,
)

router = APIRouter(
    prefix="/sides",
    tags=["sides"],
)


@router.get("/orientations", response_model=list[SideOrientationListOutput])
def get_side_orientation_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a list of side orientations.

    Returns:
        - A list of side orientations.
    """
    query = select(SideOrientation)
    return session.exec(query).all()


@router.get("/orientations/{id}", response_model=SideOrientationDetailReadOutput)
def get_side_orientation_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a side orientation by its ID.

    Parameters:
        - id (int): The ID of the side orientation to retrieve.
    Returns:
        - SideOrientationDetailReadOutput: The details of the side orientation.
    Raises:
        - HTTPException: If the ID is not provided or is not an integer.
        - HTTPException: If the side orientation is not found.
        - HTTPException: If there is an error while retrieving the side orientation.
    """
    if not id or not isinstance(id, int):
        raise HTTPException(status_code=404, detail="Side Orientation ID is required")

    try:
        side_orientation = session.get(SideOrientation, id)
        if side_orientation:
            return side_orientation
        else:
            raise HTTPException(status_code=404, detail="Side Orientation not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.post("/orientations", response_model=SideOrientationDetailWriteOutput, status_code=201)
def create_side_orientation(side_orientation_input: SideOrientationInput, session: Session = Depends(get_session)):
    """
    Create a new side orientation record.
    Parameters:
        - side_orientation_input (SideOrientationInput): The input data for the side orientation.
    Returns:
        - SideOrientationDetailWriteOutput: The created side orientation record.
    """
    if not side_orientation_input:
        raise HTTPException(status_code=400, detail="Side Orientation data is required")

    # Create a new side orientation
    new_side_orientation = SideOrientation(**side_orientation_input.model_dump())

    try:
        session.add(new_side_orientation)
        session.commit()
        session.refresh(new_side_orientation)

        return new_side_orientation

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.patch("/orientations/{id}", response_model=SideOrientationDetailWriteOutput)
def update_side_orientation(id: int, side_orientation: SideOrientationInput, session: Session = Depends(get_session)):
    """
    Update a side orientation record by its id.

    Parameters:
        - id (int): The id of the side orientation record to update.
        - side_orientation (SideOrientationInput): The updated side orientation data.

    Returns:
        - SideOrientationDetailWriteOutput: The updated side orientation record.

    Raises:
        - HTTPException: If the id is missing or not an integer, or if the side orientation record is not found.
    """
    if not id or not isinstance(id, int):
        raise HTTPException(status_code=404, detail="Side Orientation ID is required")

    try:
        existing_side_orientation = session.get(SideOrientation, id)

        if not existing_side_orientation:
            raise HTTPException(status_code=404, detail="Side Orientation not found")

        mutated_data = side_orientation.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_side_orientation, key, value)

        setattr(existing_side_orientation, "update_dt", datetime.utcnow())

        session.add(existing_side_orientation)
        session.commit()
        session.refresh(existing_side_orientation)
        return existing_side_orientation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/orientations/{id}", status_code=204)
def delete_side_orientation(id: int, session: Session = Depends(get_session)):
    """
    Delete a side orientation by its ID.
    Parameters:
        - id (int): The ID of the side orientation to delete.
    Raises:
        - HTTPException: If the ID is not provided or is not an integer.
        - HTTPException: If the side orientation is not found.
        - HTTPException: If there is an error during the deletion process.
    Returns:
        - Response: A response indicating the success of the deletion.
    """
    side_orientation = session.get(SideOrientation, id)
    if side_orientation:
        session.delete(side_orientation)
        session.commit()
    else:
        raise HTTPException(status_code=404)
