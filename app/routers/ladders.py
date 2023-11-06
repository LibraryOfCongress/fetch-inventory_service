from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.ladders import Ladder
from app.schemas.ladders import (
    LadderInput,
    LadderListOutput,
    LadderDetailWriteOutput,
    LadderDetailReadOutput,
)


router = APIRouter(
    prefix="/ladders",
    tags=["ladders"],
)


@router.get("/", response_model=list[LadderListOutput])
def get_ladder_list(session: Session = Depends(get_session)) -> list:
    query = select(Ladder)
    return session.exec(query).all()


@router.get("/{id}", response_model=LadderDetailReadOutput)
def get_ladder_detail(id: int, session: Session = Depends(get_session)):
    ladder = session.get(Ladder, id)
    if ladder:
        return ladder
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=LadderDetailWriteOutput)
def create_ladder(ladder_input: LadderInput, session: Session = Depends(get_session)) -> Ladder:
    """
    Create a ladder:

    - **side_id**: Required integer id for related side
    - **ladder_number_id**: Required integer id for related ladder number
    - **barcode**: Optional uuid for related barcode
    """
    new_ladder = Ladder(**ladder_input.model_dump())
    session.add(new_ladder)
    session.commit()
    session.refresh(new_ladder)
    return new_ladder


@router.patch("/{id}", response_model=LadderDetailWriteOutput)
def update_ladder(id: int, ladder: LadderInput, session: Session = Depends(get_session)):
    try:
        existing_ladder = session.get(Ladder, id)
        if not existing_ladder:
            raise HTTPException(status_code=404)
        mutated_data = ladder.model_dump(exclude_unset=True)
        for key, value in mutated_data.items():
            setattr(existing_ladder, key, value)
        setattr(existing_ladder, "update_dt", datetime.utcnow())
        session.add(existing_ladder)
        session.commit()
        session.refresh(existing_ladder)
        return existing_ladder
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_ladder(id: int, session: Session = Depends(get_session)):
    ladder = session.get(Ladder, id)
    if ladder:
        session.delete(ladder)
        session.commit()
    else:
        raise HTTPException(status_code=404)
