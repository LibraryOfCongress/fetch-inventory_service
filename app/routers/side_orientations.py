from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
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


@router.get("/orientations", response_model=Page[SideOrientationListOutput])
def get_side_orientation_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of side orientations.
    Returns:
        - list: A paginated list of side orientations.
    """
    return paginate(session, select(SideOrientation))


@router.get("/orientations/{id}", response_model=SideOrientationDetailReadOutput)
def get_side_orientation_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a side orientation by its ID.
    Parameters:
        - id (int): The ID of the side orientation to retrieve.
    Returns:
        - SideOrientationDetailReadOutput: The details of the side orientation.
    Raises:
        - HTTPException: If the side orientation is not found.
    """
    side_orientation = session.get(SideOrientation, id)

    if side_orientation:
        return side_orientation
    else:
        raise HTTPException(status_code=404, detail="Side Orientation not found")


@router.post(
    "/orientations", response_model=SideOrientationDetailWriteOutput, status_code=201
)
def create_side_orientation(
    side_orientation_input: SideOrientationInput,
    session: Session = Depends(get_session),
):
    """
    Create a new side orientation record.
    Parameters:
        - side_orientation_input (SideOrientationInput): The input data for the side orientation.
    Returns:
        - SideOrientationDetailWriteOutput: The created side orientation record.
    """
    # Create a new side orientation
    new_side_orientation = SideOrientation(**side_orientation_input.model_dump())
    session.add(new_side_orientation)
    session.commit()
    session.refresh(new_side_orientation)
    return new_side_orientation


@router.patch("/orientations/{id}", response_model=SideOrientationDetailWriteOutput)
def update_side_orientation(
    id: int,
    side_orientation: SideOrientationInput,
    session: Session = Depends(get_session),
):
    """
    Update a side orientation by its ID.
    Args:
        - id (int): The ID of the side orientation to update.
        - side_orientation (SideOrientationInput): The updated side orientation data.
    Returns:
        - SideOrientationDetailWriteOutput: The updated side orientation.
    Raises:
        - HTTPException: If the side orientation is not found or an error occurs during the update.
    """
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
    Deletes a side orientation with the given ID.
    Parameters:
        - id (int): The ID of the side orientation to delete.
    Returns:
        - None
    Raises:
        - HTTPException: If no side orientation with the given ID is found.
    """
    side_orientation = session.get(SideOrientation, id)

    if side_orientation:
        session.delete(side_orientation)
        session.commit()
    else:
        raise HTTPException(status_code=404)
