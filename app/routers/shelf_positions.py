from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.shelf_positions import ShelfPosition
from app.schemas.shelf_positions import (
    ShelfPositionInput,
    ShelfPositionUpdateInput,
    ShelfPositionListOutput,
    ShelfPositionDetailReadOutput,
    ShelfPositionDetailWriteOutput,
)


router = APIRouter(
    prefix="/shelves/positions",
    tags=["shelves"],
)


@router.get("/", response_model=Page[ShelfPositionListOutput])
def get_shelf_position_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a list of shelf positions.

    **Returns:**
    - Shelf Position List Output: The paginated list of shelf positions.
    """
    return paginate(session, select(ShelfPosition))


@router.get("/{id}", response_model=ShelfPositionDetailReadOutput)
def get_shelf_position_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve a shelf position detail by its ID.

    **Parameters:**
    - id: The ID of the shelf position.

    **Returns:**
    - Shelf Position Detail Read Output: The shelf position detail.

    **Raises:**
    - HTTPException: If the shelf position is not found.
    """
    shelf_position = session.get(ShelfPosition, id)
    if shelf_position:
        return shelf_position
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=ShelfPositionDetailWriteOutput, status_code=201)
def create_shelf_position(
    shelf_position_input: ShelfPositionInput, session: Session = Depends(get_session)
) -> ShelfPosition:
    """
    Create a new shelf position.

    **Args:**
    - Shelf Position Input: Input data for creating a shelf position.

    **Returns:**
    - Shelf Position: The newly created shelf position.

    **Raises:**
    - HTTPException: If there is an integrity error when adding the shelf position to
    the database.
    """
    new_shelf_position = ShelfPosition(**shelf_position_input.model_dump())
    session.add(new_shelf_position)
    session.commit()
    session.refresh(new_shelf_position)
    return new_shelf_position


@router.patch("/{id}", response_model=ShelfPositionDetailWriteOutput)
def update_shelf_position(
    id: int,
    shelf_position: ShelfPositionUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a shelf position with the given ID.

    **Args:**
    - id: The ID of the shelf position to update.
    - Shelf Position Update Input: The updated shelf position data.

    **Raises:**
    - HTTPException: If the shelf position with the given ID does not exist or if
    there is an internal server error.

    **Returns:**
    - Shelf Position Detail WriteOutput: The updated shelf position.
    """

    existing_shelf_position = session.get(ShelfPosition, id)

    if existing_shelf_position is None:
        raise HTTPException(status_code=404)

    mutated_data = shelf_position.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_shelf_position, key, value)

    setattr(existing_shelf_position, "update_dt", datetime.utcnow())
    session.add(existing_shelf_position)
    session.commit()
    session.refresh(existing_shelf_position)
    return existing_shelf_position


@router.delete("/{id}")
def delete_shelf_position(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelf position by its ID.

    **Args:**
    - id: The ID of the shelf position to delete.

    **Raises:**
    - HTTPException: If the shelf position does not exist.

    **Returns:**
    - None
    """
    shelf_position = session.get(ShelfPosition, id)

    if shelf_position:
        session.delete(shelf_position)
        session.commit()
        return HTTPException(status_code=204)
    else:
        raise HTTPException(status_code=404)
