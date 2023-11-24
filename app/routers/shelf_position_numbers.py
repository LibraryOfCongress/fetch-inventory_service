from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.schemas.shelf_position_numbers import (
    ShelfPositionNumberInput,
    ShelfPositionNumberListOutput,
    ShelfPositionNumberDetailOutput,
)


router = APIRouter(
    prefix="/shelves/positions",
    tags=["shelves"],
)


@router.get("/numbers", response_model=Page[ShelfPositionNumberListOutput])
def get_shelf_position_number_list(session: Session = Depends(get_session)) -> list:
    return paginate(session, select(ShelfPositionNumber))


@router.get("/numbers/{id}", response_model=ShelfPositionNumberDetailOutput)
def get_shelf_position_number_detail(id: int, session: Session = Depends(get_session)):
    shelf_position_number = session.get(ShelfPositionNumber, id)
    if shelf_position_number:
        return shelf_position_number
    else:
        raise HTTPException(status_code=404)


@router.post("/numbers", response_model=ShelfPositionNumberDetailOutput)
def create_shelf_position_number(shelf_position_number_input: ShelfPositionNumberInput, session: Session = Depends(get_session)) -> ShelfPositionNumber:
    """
    Create a shelf position number:

    - **number**: Required unique integer that represents a shelf position number
    """
    try:
        new_shelf_position_number = ShelfPositionNumber(**shelf_position_number_input.model_dump())
        session.add(new_shelf_position_number)
        session.commit()
        session.refresh(new_shelf_position_number)
        return new_shelf_position_number
    except IntegrityError as e:
        raise HTTPException(status_code=422, detail=f"{e}")


@router.patch("/numbers/{id}", response_model=ShelfPositionNumberDetailOutput)
def update_shelf_position_number(id: int, shelf_position_number: ShelfPositionNumberInput, session: Session = Depends(get_session)):
    try:
        existing_shelf_position_number = session.get(ShelfPositionNumber, id)
        if not existing_shelf_position_number:
            raise HTTPException(status_code=404)
        mutated_data = shelf_position_number.model_dump(exclude_unset=True)
        for key, value in mutated_data.items():
            setattr(existing_shelf_position_number, key, value)
        setattr(existing_shelf_position_number, "update_dt", datetime.utcnow())
        session.add(existing_shelf_position_number)
        session.commit()
        session.refresh(existing_shelf_position_number)
        return existing_shelf_position_number
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/numbers/{id}", status_code=204)
def delete_shelf_position_number(id: int, session: Session = Depends(get_session)):
    shelf_position_number = session.get(ShelfPositionNumber, id)
    if shelf_position_number:
        session.delete(shelf_position_number)
        session.commit()
    else:
        raise HTTPException(status_code=404)
