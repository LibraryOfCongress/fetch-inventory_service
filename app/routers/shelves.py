import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.shelves import Shelf
from app.schemas.shelves import (
    ShelfInput,
    ShelfUpdateInput,
    ShelfListOutput,
    ShelfDetailWriteOutput,
    ShelfDetailReadOutput,
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


LOGGER = logging.getLogger("app.routers.shelves")


@router.get("/", response_model=Page[ShelfListOutput])
def get_shelf_list(session: Session = Depends(get_session)) -> list:
    """
    Get a list of shelves.

    **Returns:**
    - Shelf List Output: The paginated list of shelves.
    """
    return paginate(session, select(Shelf))


@router.get("/{id}", response_model=ShelfDetailReadOutput)
def get_shelf_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a shelf with the given ID.

    **Args:**
    - id: The ID of the shelf to retrieve.

    **Returns:**
    - Shelf Detail Read Output: The details of the retrieved shelf.

    **Raises:**
    - HTTPException: If the shelf with the specified ID is not found.
    """
    shelf = session.get(Shelf, id)

    if shelf:
        return shelf

    raise NotFound(detail=f"Shelf ID {id} Not Found")


@router.post("/", response_model=ShelfDetailWriteOutput, status_code=201)
def create_shelf(
    shelf_input: ShelfInput, session: Session = Depends(get_session)
) -> Shelf:
    """
    Create a shelf:

    **Args:**
    - Shelf Input: The input data for creating the shelf.

    **Returns:**
    - Shelf Detail Write Output: The newly created shelf.

    **Notes:**
    - **ladder_id**: Required integer id for parent ladder
    - **container_type_id**: Required integer id for related container type
    - **shelf_number_id**: Required integer id for related shelf number
    - **barcode_id**: Optional uuid for related barcode
    - **capacity**: Required integer representing maximum shelf positions supported
    - **height**: Required numeric (scale 4, precision 2) height in inches
    - **width**: Required numeric (scale 4, precision 2) width in inches
    - **depth**: Required numeric (scale 4, precision 2) depth in inches
    """
    try:
        new_shelf = Shelf(**shelf_input.model_dump())
        session.add(new_shelf)
        session.commit()
        session.refresh(new_shelf)

        return new_shelf

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=ShelfDetailWriteOutput)
def update_shelf(
    id: int, shelf: ShelfUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a shelf with the given ID.

    **Args:**
    - id: The ID of the shelf to update.
    - Shelf Update Input: The updated shelf data.

    **Raises:**
    - HTTPException: If the shelf with the given ID does not exist or if there is a
    server error.

    **Returns:**
    - Shelf Detail Write Output: The updated shelf.
    """
    try:
        existing_shelf = session.get(Shelf, id)

        if existing_shelf is None:
            raise NotFound(detail=f"Shelf ID {id} Not Found")

        mutated_data = shelf.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_shelf, key, value)

        setattr(existing_shelf, "update_dt", datetime.utcnow())
        session.add(existing_shelf)
        session.commit()
        session.refresh(existing_shelf)

        return existing_shelf

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_shelf(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelf by its ID.

    **Args:**
    - id: The ID of the shelf to delete.

    **Raises:**
    - HTTPException: If the shelf with the given id is not found.

    **Returns:**
    - None
    """
    shelf = session.get(Shelf, id)

    if shelf:
        session.delete(shelf)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Shelf ID {id} Deleted "
                                    f"Successfully"
        )

    raise NotFound(detail=f"Shelf ID {id} Not Found")
