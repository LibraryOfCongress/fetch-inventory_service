from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.side_orientations import SideOrientation

from app.schemas.side_orientations import (
    SideOrientationInput,
    SideOrientationListOutput,
    SideOrientationDetailWriteOutput,
    SideOrientationDetailReadOutput,
    SideOrientationUpdateInput
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

router = APIRouter(
    prefix="/sides",
    tags=["sides"],
)


@router.get("/orientations", response_model=Page[SideOrientationListOutput])
def get_side_orientation_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of side orientations.

    **Returns**:
    - list: A paginated list of side orientations.
    """
    return paginate(session, select(SideOrientation))


@router.get("/orientations/{id}", response_model=SideOrientationDetailReadOutput)
def get_side_orientation_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a side orientation by its ID.

    **Parameters**:
    - id: The ID of the side orientation to retrieve.

    **Returns**:
    - Side Orientation Detail Read Output: The details of the side orientation.

    **Raises**:
    - HTTPException: If the side orientation is not found.
    """

    side_orientation = session.get(SideOrientation, id)

    if side_orientation:
        return side_orientation

    raise NotFound(detail=f"Side Orientation ID {id} Not Found")


@router.post(
    "/orientations", response_model=SideOrientationDetailWriteOutput, status_code=201
)
def create_side_orientation(
    side_orientation_input: SideOrientationInput,
    session: Session = Depends(get_session),
):
    """
    Create a new side orientation record.

    **Parameters**:
    - Side Orientation Input: The input data for the side orientation.

    **Returns**:
    - Side Orientation Detail Write Output: The created side orientation record.
    """
    try:
        # Create a new side orientation
        new_side_orientation = SideOrientation(**side_orientation_input.model_dump())
        session.add(new_side_orientation)
        session.commit()
        session.refresh(new_side_orientation)

        return new_side_orientation

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")

@router.patch("/orientations/{id}", response_model=SideOrientationDetailWriteOutput)
def update_side_orientation(
    id: int,
    side_orientation: SideOrientationUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a side orientation by its ID.

    **Args**:
    - id: The ID of the side orientation to update.
    - Side Orientation Update Input: The updated side orientation data.

    **Returns**:
    - Side Orientation Detail Write Output: The updated side orientation.

    **Raises**:
    - HTTPException: If the side orientation is not found or an error occurs during the update.
    """
    try:
        existing_side_orientation = session.get(SideOrientation, id)

        if not existing_side_orientation:
            raise NotFound(detail=f"Side Orientation ID {id} Not Found")

        mutated_data = side_orientation.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_side_orientation, key, value)

        setattr(existing_side_orientation, "update_dt", datetime.utcnow())

        session.add(existing_side_orientation)
        session.commit()
        session.refresh(existing_side_orientation)

        return existing_side_orientation

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/orientations/{id}")
def delete_side_orientation(id: int, session: Session = Depends(get_session)):
    """
    Deletes a side orientation with the given ID.

    **Parameters**:
    - id: The ID of the side orientation to delete.

    **Returns**:
    - None

    **Raises**:
    - HTTPException: If no side orientation with the given ID is found.
    """
    side_orientation = session.get(SideOrientation, id)

    if side_orientation:
        session.delete(side_orientation)
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Side Orientation id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Side Orientation ID {id} Not Found")
