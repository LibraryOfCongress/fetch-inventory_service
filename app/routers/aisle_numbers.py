from typing import Sequence

from fastapi import APIRouter, HTTPException, Depends, Response
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.aisle_numbers import AisleNumber
from app.schemas.aisle_numbers import (
    AisleNumberInput,
    AisleNumberListOutput,
    AisleNumberDetailOutput,
)

router = APIRouter(
    prefix="/aisles",
    tags=["aisles"],
)


@router.get("/numbers", response_model=list[AisleNumberListOutput])
def get_aisle_number_list(session: Session = Depends(get_session)) -> list:
    query = select(AisleNumber)
    return session.exec(query).all()


@router.get("/numbers/{id}", response_model=AisleNumberDetailOutput)
def get_aisle_number_detail(id: int, session: Session = Depends(get_session)):
    aisle_number = session.get(AisleNumber, id)
    if aisle_number:
        return aisle_number
    else:
        raise HTTPException(status_code=404)


@router.post("/numbers", response_model=AisleNumberDetailOutput, status_code=201)
def create_aisle_number(
    aisle_number_input: AisleNumberInput, session: Session = Depends(get_session)
) -> AisleNumber:
    """
    Create a aisle number:

    - **number**: Required unique integer that represents a aisle number
    """
    try:
        new_aisle_number = AisleNumber(**aisle_number_input.model_dump())
        session.add(new_aisle_number)
        session.commit()
        session.refresh(new_aisle_number)
        return new_aisle_number
    except IntegrityError as e:
        raise HTTPException(status_code=422, detail=f"{e}")


@router.patch("/numbers/{id}", response_model=AisleNumberDetailOutput)
def update_aisle_number(
    id: int, aisle_number: AisleNumberInput, session: Session = Depends(get_session)
):
    try:
        existing_aisle_number = session.get(AisleNumber, id)
        if not existing_aisle_number:
            raise HTTPException(status_code=404)
        mutated_data = aisle_number.model_dump(exclude_unset=True)
        for key, value in mutated_data.items():
            setattr(existing_aisle_number, key, value)
        setattr(existing_aisle_number, "update_dt", datetime.utcnow())
        session.add(existing_aisle_number)
        session.commit()
        session.refresh(existing_aisle_number)
        return existing_aisle_number
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/numbers/{id}", status_code=204)
def delete_aisle_number(id: int, session: Session = Depends(get_session)):
    aisle_number = session.get(AisleNumber, id)
    if aisle_number:
        session.delete(aisle_number)
        session.commit()
    else:
        raise HTTPException(status_code=404)
