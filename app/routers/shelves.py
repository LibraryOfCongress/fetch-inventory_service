from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.shelves import Shelf
from app.schemas.shelves import (
    ShelfInput,
    ShelfListOutput,
    ShelfDetailWriteOutput,
    ShelfDetailReadOutput,
)


router = APIRouter(
    prefix="/shelves",
    tags=["shelves"],
)


@router.get("/", response_model=Page[ShelfListOutput])
def get_shelf_list(session: Session = Depends(get_session)) -> list:
    return paginate(session, select(Shelf))


@router.get("/{id}", response_model=ShelfDetailReadOutput)
def get_shelf_detail(id: int, session: Session = Depends(get_session)):
    shelf = session.get(Shelf, id)
    if shelf:
        return shelf
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=ShelfDetailWriteOutput)
def create_shelf(shelf_input: ShelfInput, session: Session = Depends(get_session)) -> Shelf:
    """
    Create a shelf:

    - **ladder_id**: Required integer id for parent ladder
    - **container_type_id**: Required integer id for related container type
    - **shelf_number_id**: Required integer id for related shelf number
    - **barcode_id**: Optional uuid for related barcode
    - **capacity**: Required integer representing maximum shelf positions supported
    - **height**: Required numeric (scale 4, precision 2) height in inches
    - **width**: Required numeric (scale 4, precision 2) width in inches
    - **depth**: Required numeric (scale 4, precision 2) depth in inches
    """
    new_shelf = Shelf(**shelf_input.model_dump())
    session.add(new_shelf)
    session.commit()
    session.refresh(new_shelf)
    return new_shelf


@router.patch("/{id}", response_model=ShelfDetailWriteOutput)
def update_shelf(id: int, shelf: ShelfInput, session: Session = Depends(get_session)):
    try:
        existing_shelf = session.get(Shelf, id)
        if not existing_shelf:
            raise HTTPException(status_code=404)
        mutated_data = shelf.model_dump(exclude_unset=True)
        for key, value in mutated_data.items():
            setattr(existing_shelf, key, value)
        setattr(existing_shelf, "update_dt", datetime.utcnow())
        session.add(existing_shelf)
        session.commit()
        session.refresh(existing_shelf)
        return existing_shelf
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_shelf(id: int, session: Session = Depends(get_session)):
    shelf = session.get(Shelf, id)
    if shelf:
        session.delete(shelf)
        session.commit()
    else:
        raise HTTPException(status_code=404)
