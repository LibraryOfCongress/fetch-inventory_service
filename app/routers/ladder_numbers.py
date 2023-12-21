from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.ladder_numbers import LadderNumber
from app.schemas.ladder_numbers import (
    LadderNumberInput,
    LadderNumberListOutput,
    LadderNumberDetailOutput,
)


router = APIRouter(
    prefix="/ladders",
    tags=["ladders"],
)


@router.get("/numbers", response_model=Page[LadderNumberListOutput])
def get_ladder_number_list(session: Session = Depends(get_session)) -> list:
    return paginate(session, select(LadderNumber))


@router.get("/numbers/{id}", response_model=LadderNumberDetailOutput)
def get_ladder_number_detail(id: int, session: Session = Depends(get_session)):
    ladder_number = session.get(LadderNumber, id)
    if ladder_number:
        return ladder_number
    else:
        raise HTTPException(status_code=404)


@router.post("/numbers", response_model=LadderNumberDetailOutput)
def create_ladder_number(
    ladder_number_input: LadderNumberInput, session: Session = Depends(get_session)
) -> LadderNumber:
    """
    Create a ladder number:

    - **number**: Required unique integer that represents a ladder number
    """
    try:
        new_ladder_number = LadderNumber(**ladder_number_input.model_dump())
        session.add(new_ladder_number)
        session.commit()
        session.refresh(new_ladder_number)
        return new_ladder_number
    except IntegrityError as e:
        raise HTTPException(status_code=422, detail=f"{e}")


@router.patch("/numbers/{id}", response_model=LadderNumberDetailOutput)
def update_ladder_number(
    id: int, ladder_number: LadderNumberInput, session: Session = Depends(get_session)
):
    try:
        existing_ladder_number = session.get(LadderNumber, id)
        if not existing_ladder_number:
            raise HTTPException(status_code=404)
        mutated_data = ladder_number.model_dump(exclude_unset=True)
        for key, value in mutated_data.items():
            setattr(existing_ladder_number, key, value)
        setattr(existing_ladder_number, "update_dt", datetime.utcnow())
        session.add(existing_ladder_number)
        session.commit()
        session.refresh(existing_ladder_number)
        return existing_ladder_number
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/numbers/{id}", status_code=204)
def delete_ladder_number(id: int, session: Session = Depends(get_session)):
    ladder_number = session.get(LadderNumber, id)
    if ladder_number:
        session.delete(ladder_number)
        session.commit()
    else:
        raise HTTPException(status_code=404)
