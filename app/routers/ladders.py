from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.ladders import Ladder
from app.schemas.ladders import (
    LadderInput,
    LadderUpdateInput,
    LadderListOutput,
    LadderDetailWriteOutput,
    LadderDetailReadOutput,
)


router = APIRouter(
    prefix="/ladders",
    tags=["ladders"],
)


@router.get("/", response_model=Page[LadderListOutput])
def get_ladder_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of ladders.

    **Returns:**
    - Ladder List Output: A list of ladders.
    """
    return paginate(session, select(Ladder))


@router.get("/{id}", response_model=LadderDetailReadOutput)
def get_ladder_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a ladder by its ID.

    **Args:**
    - id: The ID of the ladder to retrieve.

    **Returns:**
    - Ladder Detail Read Output: The details of the ladder.

    **Raises:**
    - HTTPException: If the ladder is not found.
    """
    ladder = session.get(Ladder, id)

    if ladder:
        return ladder
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=LadderDetailWriteOutput, status_code=201)
def create_ladder(
    ladder_input: LadderInput, session: Session = Depends(get_session)
) -> Ladder:
    """
    Create a ladder:

    **Args:**
    - Ladder Input: The input data for creating a ladder.

    **Returns:**
    - Ladder Detail Write Output: The created ladder.

    **Raises:**
    - HTTPException: If the ladder already exists.

    **Notes:**
    - **side_id**: Required integer id for related side
    - **ladder_number_id**: Required integer id for related ladder number
    """
    new_ladder = Ladder(**ladder_input.model_dump())
    session.add(new_ladder)
    session.commit()
    session.refresh(new_ladder)
    return new_ladder


@router.patch("/{id}", response_model=LadderDetailWriteOutput)
def update_ladder(
    id: int, ladder: LadderUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a ladder with the given ID.

    **Args:**
    - id: The ID of the ladder to update.
    - Ladder Update Input: The updated ladder data.

    **Returns:**
    - Ladder Detail Write Output: The updated ladder.

    **Raises:**
    - HTTPException: If the ladder with the given ID is not found.
    """

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


@router.delete("/{id}")
def delete_ladder(id: int, session: Session = Depends(get_session)):
    """
    Delete a ladder with the given ID.

    **Args:**
    - id: The ID of the ladder to delete.

    **Returns:**
    - None

    **Raises:**
    - HTTPException: If the ladder with the given ID is not found.
    """
    ladder = session.get(Ladder, id)

    if ladder:
        session.delete(ladder)
        session.commit()
        return HTTPException(status_code=204)
    else:
        raise HTTPException(status_code=404)
