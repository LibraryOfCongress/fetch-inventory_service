from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.shelf_positions import ShelfPosition
from app.schemas.shelf_positions import (
    ShelfPositionInput,
    ShelfPositionListOutput,
    ShelfPositionDetailReadOutput,
    ShelfPositionDetailWriteOutput
)


router = APIRouter(
    prefix="/shelves/positions",
    tags=["shelves"],
)


@router.get("/", response_model=list[ShelfPositionListOutput])
def get_shelf_position_list(session: Session = Depends(get_session)) -> list:
    query = select(ShelfPosition)
    return session.exec(query).all()


@router.get("/{id}", response_model=ShelfPositionDetailReadOutput)
def get_shelf_position_detail(id: int, session: Session = Depends(get_session)):
    shelf_position = session.get(ShelfPosition, id)
    if shelf_position:
        return shelf_position
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=ShelfPositionDetailWriteOutput)
def create_shelf_position(shelf_position_input: ShelfPositionInput, session: Session = Depends(get_session)) -> ShelfPosition:
    """
    Create a shelf position
    """
    try:
        new_shelf_position = ShelfPosition(**shelf_position_input.model_dump())
        session.add(new_shelf_position)
        session.commit()
        session.refresh(new_shelf_position)
        return new_shelf_position
    except IntegrityError as e:
        raise HTTPException(status_code=422, detail=f"{e}")


@router.patch("/{id}", response_model=ShelfPositionDetailWriteOutput)
def update_shelf_position(id: int, shelf_position: ShelfPositionInput, session: Session = Depends(get_session)):
    try:
        existing_shelf_position = session.get(ShelfPosition, id)
        if not existing_shelf_position:
            raise HTTPException(status_code=404)
        mutated_data = shelf_position.model_dump(exclude_unset=True)
        for key, value in mutated_data.items():
            setattr(existing_shelf_position, key, value)
        setattr(existing_shelf_position, "update_dt", datetime.utcnow())
        session.add(existing_shelf_position)
        session.commit()
        session.refresh(existing_shelf_position)
        return existing_shelf_position
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_shelf_position(id: int, session: Session = Depends(get_session)):
    shelf_position = session.get(ShelfPosition, id)
    if shelf_position:
        session.delete(shelf_position)
        session.commit()
    else:
        raise HTTPException(status_code=404)
