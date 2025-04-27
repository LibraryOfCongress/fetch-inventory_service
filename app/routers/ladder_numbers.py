from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.ladder_numbers import LadderNumber
from app.schemas.ladder_numbers import (
    LadderNumberInput,
    LadderNumberListOutput,
    LadderNumberDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)


router = APIRouter(
    prefix="/ladders",
    tags=["ladders"],
)


@router.get("/numbers", response_model=Page[LadderNumberListOutput])
def get_ladder_number_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of ladder numbers.

    **Returns:**
    - Ladder Number List Output: A list of ladder numbers with pagination metadata.
    """
    return paginate(session, select(LadderNumber))


@router.get("/numbers/{id}", response_model=LadderNumberDetailOutput)
def get_ladder_number_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve details of a ladder number by its ID.

    **Args:**
    - id: The ID of the ladder number.

    **Returns:**
    - Ladder Number Detail Output: The ladder number details.

    **Raises:**
    - HTTPException: If the ladder number is not found.
    """
    ladder_number = session.get(LadderNumber, id)

    if ladder_number:
        return ladder_number

    raise NotFound(detail=f"Ladder Number ID {id} Not Found")


@router.post("/numbers", response_model=LadderNumberDetailOutput, status_code=201)
def create_ladder_number(
    ladder_number_input: LadderNumberInput, session: Session = Depends(get_session)
) -> LadderNumber:
    """
    Create a ladder number:

    **Args:**
    - Ladder Number Input: The input data for creating the ladder
    number.

    **Returns:**
    - Ladder Number Detail Output: The newly created ladder number.

    **Notes:**
    - **number**: Required unique integer that represents a ladder number
    """
    try:
        new_ladder_number = LadderNumber(**ladder_number_input.model_dump())
        session.add(new_ladder_number)
        session.commit()
        session.refresh(new_ladder_number)

        return new_ladder_number

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/numbers/{id}", response_model=LadderNumberDetailOutput)
def update_ladder_number(
    id: int, ladder_number: LadderNumberInput, session: Session = Depends(get_session)
):
    """
    Updates a ladder number with the provided input data.

    **Args:**
    - id: The ID of the ladder number to update.
    - Ladder Number Input: The input data to update the ladder number.

    **Returns:**
    - Ladder Number Detail Output: The updated ladder number.
    """
    try:
        existing_ladder_number = session.get(LadderNumber, id)

        if not existing_ladder_number:
            raise NotFound(detail=f"Ladder Number ID {id} Not Found")

        mutated_data = ladder_number.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_ladder_number, key, value)

        setattr(existing_ladder_number, "update_dt", datetime.utcnow())
        session.add(existing_ladder_number)
        session.commit()
        session.refresh(existing_ladder_number)

        return existing_ladder_number

    except Exception as e:
        raise InternalServerError(detail=f"{e}")

@router.delete("/numbers/{id}")
def delete_ladder_number(id: int, session: Session = Depends(get_session)):
    """
    Deletes a ladder number from the database.

    **Args:**
    - id: The ID of the ladder number to delete.

    **Returns:**
    - HTTPException: The appropriate HTTP exception based on whether the ladder
    number was found or not.
    """
    ladder_number = session.get(LadderNumber, id)

    if ladder_number:
        session.delete(ladder_number)
        session.commit()
        return HTTPException(
            status_code=204, detail=f"Ladder Number ID {id} deleted "
                                    f"successfully"
        )

    raise NotFound(detail=f"Ladder Number ID {id} Not Found")
