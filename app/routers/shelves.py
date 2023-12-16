import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
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


router = APIRouter(
    prefix="/shelves",
    tags=["shelves"],
)


LOGGER = logging.getLogger("app.routers.shelves")


@router.get("/", response_model=Page[ShelfListOutput])
def get_shelf_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of shelves.

    **Returns:**
    - List of shelves
    """
    return paginate(session, select(Shelf))


@router.get("/{id}", response_model=ShelfDetailReadOutput)
def get_shelf_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a shelf given its ID.

    **Args:**
    - id (int): The ID of the shelf to retrieve.

    **Returns:**
    - Shelf Detail Read Output: The details of the retrieved shelf.

    **Raises:**
    - HTTPException: If the shelf with the specified ID is not found.
    """
    shelf = session.get(Shelf, id)
    if shelf:
        return shelf
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=ShelfDetailWriteOutput)
def create_shelf(
    shelf_input: ShelfInput, session: Session = Depends(get_session)
) -> Shelf:
    """
    Create a shelf:

    **Args:**
    - Shelf Input: The input data for creating the shelf.

    **Returns:**
    - Shelf: The newly created shelf.

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{id}", response_model=ShelfDetailWriteOutput)
def update_shelf(
    id: int, shelf: ShelfUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a shelf with the given ID using the provided shelf data.

    **Args:**
    - id (int): The ID of the shelf to update.
    - Shelf Update Input: The updated shelf data.

    **Returns:**
    - Shelf Detail Write Output: The updated shelf.

    **Raises:**
    - HTTPException: If the shelf with the given ID does not exist or if there is
        a server error.
    """
    try:
        existing_shelf = session.get(Shelf, id)

        if not existing_shelf:
            raise HTTPException(status_code=404)

        mutated_data = shelf.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_shelf, key, value)

        setattr(existing_shelf, "update_dt", datetime.utcnow())

        LOGGER.info(f"\nExisting Shelf: {existing_shelf}\n")

        session.add(existing_shelf)
        session.commit()
        session.refresh(existing_shelf)
        return existing_shelf
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_shelf(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelf with the given id.

    **Args:**
    - id (int): The id of the shelf to delete.

    **Raises:**
    - HTTPException: If the shelf with the given id is not found.

    **Returns:**
    - None
    """
    shelf = session.get(Shelf, id)
    if shelf:
        session.delete(shelf)
        session.commit()
    else:
        raise HTTPException(status_code=404)
