from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.shelf_numbers import ShelfNumber
from app.schemas.shelf_numbers import (
    ShelfNumberInput,
    ShelfNumberListOutput,
    ShelfNumberDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)


router = APIRouter(
    prefix="/shelves",
    tags=["shelves"],
)


@router.get("/numbers", response_model=Page[ShelfNumberListOutput])
def get_shelf_number_list(session: Session = Depends(get_session)) -> list:
    """
    Get a paginated list of shelf numbers.

    **Returns:**
    - Shelf Number List Output: The paginated list of shelf numbers.
    """
    return paginate(session, select(ShelfNumber))


@router.get("/numbers/{id}", response_model=ShelfNumberDetailOutput)
def get_shelf_number_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve details of a shelf number by ID.

    **Parameters:**
    - id: The ID of the shelf number to retrieve.

    **Returns:**
    - Shelf Number Detail Output: The details of the shelf number.

    **Raises:**
    - HTTPException: If the shelf number is not found.
    """
    shelf_number = session.get(ShelfNumber, id)

    if shelf_number:
        return shelf_number

    raise NotFound(detail=f"Shelf Number ID {id} Not Found")


@router.post("/numbers", response_model=ShelfNumberDetailOutput, status_code=201)
def create_shelf_number(
    shelf_number_input: ShelfNumberInput, session: Session = Depends(get_session)
) -> ShelfNumber:
    """
    Create a shelf number:

    **Args:**
    - Shelf Number Input: The input data for creating a shelf number.

    **Returns:**
    - Shelf Number: The newly created shelf number.

    **Notes:**
    - **number**: Required unique integer that represents a shelf number
    """
    try:
        new_shelf_number = ShelfNumber(**shelf_number_input.model_dump())
        session.add(new_shelf_number)
        session.commit()
        session.refresh(new_shelf_number)

        return new_shelf_number

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/numbers/{id}", response_model=ShelfNumberDetailOutput)
def update_shelf_number(
    id: int, shelf_number: ShelfNumberInput, session: Session = Depends(get_session)
):
    """
    Update a shelf number in the database.

    **Args:**
    - id: The ID of the shelf number to update.
    - Shelf Number Input: The updated shelf number data.

    **Returns:**
    - Shelf Number: The updated shelf number.

    **Raises:**
    - HTTPException: If the shelf number does not exist (404) or if there is a server
    error (500).
    """
    try:
        existing_shelf_number = session.get(ShelfNumber, id)

        if existing_shelf_number is None:
            raise NotFound(detail=f"Shelf Number ID {id} Not Found")

        mutated_data = shelf_number.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_shelf_number, key, value)

        setattr(existing_shelf_number, "update_dt", datetime.utcnow())
        session.add(existing_shelf_number)
        session.commit()
        session.refresh(existing_shelf_number)

        return existing_shelf_number

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/numbers/{id}")
def delete_shelf_number(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelf number by ID.

    **Args:**
    - id (int): The ID of the shelf number to delete.

    **Raises:**
    - HTTPException: If the shelf number with the given ID does not exist.

    **Returns:**
    - None
    """
    shelf_number = session.get(ShelfNumber, id)

    if shelf_number:
        session.delete(shelf_number)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Shelf Number ID {id} Deleted "
                                    f"Successfully"
        )

    raise NotFound(detail=f"Shelf Number ID {id} Not Found")
