from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.schemas.shelf_position_numbers import (
    ShelfPositionNumberInput,
    ShelfPositionNumberListOutput,
    ShelfPositionNumberDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter

router = APIRouter(
    prefix="/shelves/positions",
    tags=["shelves"],
)


@router.get("/numbers", response_model=Page[ShelfPositionNumberListOutput])
def get_shelf_position_number_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of shelf position numbers.

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.

    Returns:
    - Shelf Position Number List Output: The paginated list of shelf position numbers.
    """
    # Create a query to select all SShelf Position Number
    query = select(ShelfPositionNumber).distinct()

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(ShelfPositionNumber)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/numbers/{id}", response_model=ShelfPositionNumberDetailOutput)
def get_shelf_position_number_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a shelf position number.

    **Args:**
    - id: The ID of the shelf position number.

    **Returns:**
    - Shelf Position Number Detail Output: The details of the shelf position number.

    **Raises:**
        HTTPException: If the shelf position number is not found.
    """
    shelf_position_number = session.get(ShelfPositionNumber, id)

    if shelf_position_number:
        return shelf_position_number

    raise NotFound(detail=f"Shelf Position Number ID {id} Not Found")


@router.post(
    "/numbers", response_model=ShelfPositionNumberDetailOutput, status_code=201
)
def create_shelf_position_number(
    shelf_position_number_input: ShelfPositionNumberInput,
    session: Session = Depends(get_session),
) -> ShelfPositionNumber:
    """
    Create a shelf position number:

    **Args:**
    - Shelf Position Number Input: Input data for the new
    shelf position number.

    **Returns:**
    - Shelf Position Number: The newly created shelf position number.

    **Raises:**
    - HTTPException: If there is an integrity error when inserting the new shelf
    position number.

    **Notes:**
    - **number**: Required unique integer that represents a shelf position number
    """
    try:
        new_shelf_position_number = ShelfPositionNumber(
            **shelf_position_number_input.model_dump()
        )
        session.add(new_shelf_position_number)
        session.commit()
        session.refresh(new_shelf_position_number)

        return new_shelf_position_number

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/numbers/{id}", response_model=ShelfPositionNumberDetailOutput)
def update_shelf_position_number(
    id: int,
    shelf_position_number: ShelfPositionNumberInput,
    session: Session = Depends(get_session),
):
    """
    Update a shelf position number in the database.

    **Args:**
    - id: The ID of the shelf position number to update.
    - Shelf Position Number Input: The updated shelf position
    number data.

    **Returns:**
    - Shelf Position Number Detail Output: The updated shelf position number object.

    **Raises:**
    - HTTPException: If the shelf position number with the given ID is not found or
    an error occurs during the update.
    """
    try:
        existing_shelf_position_number = session.get(ShelfPositionNumber, id)

        if existing_shelf_position_number is None:
            raise NotFound(detail=f"Shelf Position Number ID {id} Not Found")

        mutated_data = shelf_position_number.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_shelf_position_number, key, value)

        setattr(existing_shelf_position_number, "update_dt", datetime.now(timezone.utc))
        session.add(existing_shelf_position_number)
        session.commit()
        session.refresh(existing_shelf_position_number)

        return existing_shelf_position_number

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/numbers/{id}")
def delete_shelf_position_number(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelf position number by its ID.
    **Args:**
    - id (int): The ID of the shelf position number to delete.

    **Returns:**
    - None

    **Raises:**
    - HTTPException: If the shelf position number is not found.
    """
    shelf_position_number = session.get(ShelfPositionNumber, id)

    if shelf_position_number:
        session.delete(shelf_position_number)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Shelf Position Number ID {id} Deleted "
                                    f"Successfully"
        )

    raise NotFound(detail=f"Shelf Position Number ID {id} Not Found")
