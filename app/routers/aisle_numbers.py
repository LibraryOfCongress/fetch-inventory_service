from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
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


@router.get("/numbers", response_model=Page[AisleNumberListOutput])
def get_aisle_number_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of aisle numbers.

    **Returns**:
    - Aisle Number List Output: The paginated list of aisle numbers.
    """
    return paginate(session, select(AisleNumber))


@router.get("/numbers/{id}", response_model=AisleNumberDetailOutput)
def get_aisle_number_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the aisle number detail for the given ID.

    **Parameters**:
    - id: The ID of the aisle number.

    **Returns**:
    - Aisle Number Detail Output: The aisle number detail if found.

    **Raises**:
    - HTTPException: If the aisle number is not found.
    """
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
    Create a new aisle number:

    **Args**:
    - Aisle Number Input: The input data for the aisle number.

    **Returns**:
    - Aisle Number: The created aisle number.

    **Raises**:
    - HTTPException: If there is an integrity error.

    **Notes**:
    - **number**: Required unique integer that represents a aisle number
    """

    new_aisle_number = AisleNumber(**aisle_number_input.model_dump())
    session.add(new_aisle_number)
    session.commit()
    session.refresh(new_aisle_number)
    return new_aisle_number


@router.patch("/numbers/{id}", response_model=AisleNumberDetailOutput)
def update_aisle_number(
    id: int, aisle_number: AisleNumberInput, session: Session = Depends(get_session)
):
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


@router.delete("/numbers/{id}")
def delete_aisle_number(id: int, session: Session = Depends(get_session)):
    """
    Delete an aisle number by its ID.

    **Args**:
    - id: The ID of the aisle number to delete.

    **Raises**:
    - HTTPException: If the aisle number with the given ID does not exist.

    **Returns**:
    - None
    """
    aisle_number = session.get(AisleNumber, id)

    if aisle_number:
        session.delete(aisle_number)
        session.commit()
        return HTTPException(status_code=204)
    else:
        raise HTTPException(status_code=404)
