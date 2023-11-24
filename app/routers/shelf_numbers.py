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


router = APIRouter(
    prefix="/shelves",
    tags=["shelves"],
)


@router.get("/numbers", response_model=Page[ShelfNumberListOutput])
def get_shelf_number_list(session: Session = Depends(get_session)) -> list:
    return paginate(session, select(ShelfNumber))


@router.get("/numbers/{id}", response_model=ShelfNumberDetailOutput)
def get_shelf_number_detail(id: int, session: Session = Depends(get_session)):
    shelf_number = session.get(ShelfNumber, id)
    if shelf_number:
        return shelf_number
    else:
        raise HTTPException(status_code=404)


@router.post("/numbers", response_model=ShelfNumberDetailOutput)
def create_shelf_number(shelf_number_input: ShelfNumberInput, session: Session = Depends(get_session)) -> ShelfNumber:
    """
    Create a shelf number:

    - **number**: Required unique integer that represents a shelf number
    """
    try:
        new_shelf_number = ShelfNumber(**shelf_number_input.model_dump())
        session.add(new_shelf_number)
        session.commit()
        session.refresh(new_shelf_number)
        return new_shelf_number
    except IntegrityError as e:
        raise HTTPException(status_code=422, detail=f"{e}")


@router.patch("/numbers/{id}", response_model=ShelfNumberDetailOutput)
def update_shelf_number(id: int, shelf_number: ShelfNumberInput, session: Session = Depends(get_session)):
    try:
        existing_shelf_number = session.get(ShelfNumber, id)
        if not existing_shelf_number:
            raise HTTPException(status_code=404)
        mutated_data = shelf_number.model_dump(exclude_unset=True)
        for key, value in mutated_data.items():
            setattr(existing_shelf_number, key, value)
        setattr(existing_shelf_number, "update_dt", datetime.utcnow())
        session.add(existing_shelf_number)
        session.commit()
        session.refresh(existing_shelf_number)
        return existing_shelf_number
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/numbers/{id}", status_code=204)
def delete_shelf_number(id: int, session: Session = Depends(get_session)):
    shelf_number = session.get(ShelfNumber, id)
    if shelf_number:
        session.delete(shelf_number)
        session.commit()
    else:
        raise HTTPException(status_code=404)
