import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.database.session import get_session
from app.models.aisles import Aisle
from app.schemas.aisles import (
    AisleInput,
    AisleUpdateInput,
    AisleListOutput,
    AisleDetailWriteOutput,
    AisleDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

import traceback


router = APIRouter(
    prefix="/aisles",
    tags=["aisles"],
)


@router.get("/", response_model=Page[AisleListOutput])
def get_aisle_list(session: Session = Depends(get_session)) -> list:
    """
    Get a paginated list of aisles.

    **Returns**:
    - Aisle List Output: The paginated list of aisles.
    """
    return paginate(session, select(Aisle))


@router.get("/{id}", response_model=AisleDetailReadOutput)
def get_aisle_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of an aisle from the database using the provided ID.

    **Args**:
    - id: The ID of the aisle.

    **Returns**:
    - Aisle Detail Read Output: The details of the aisle.

    **Raises**:
    - HTTPException: If the aisle is not found in the database.
    """
    # Retrieve the aisle from the database using the provided ID
    aisle = session.get(Aisle, id)

    if aisle:
        return aisle

    raise NotFound(detail=f"Aisle ID {id} Not Found")


@router.post("/", response_model=AisleDetailWriteOutput, status_code=201)
def create_aisle(aisle_input: AisleInput, session: Session = Depends(get_session)):
    """
    Create a new aisle.

    **Args**:
    - Aisle Input: The input data for creating a new aisle.

    **Returns**:
    - Aisle Detail Write Output: The created aisle.

    **Raises**:
    - HTTPException: If building_id and module_id are both set.
    """
    try:
        # Create a new Aisle object
        new_aisle = Aisle(**aisle_input.model_dump())
        session.add(new_aisle)
        session.commit()
        session.refresh(new_aisle)

        return new_aisle

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=AisleDetailWriteOutput)
def update_aisle(
    id: int, aisle: AisleUpdateInput, session: Session = Depends(get_session)
):
    """
    Updates an aisle with the given ID using the provided aisle data.

    **Args**:
    - id: The ID of the aisle to update.
    - Aisle Update Input: The updated aisle data.

    **Returns**:
    - Aisle Detail Write Output: The updated aisle.
    """
    try:
        # Get the existing aisle
        existing_aisle = session.get(Aisle, id)

        if not existing_aisle:
            raise NotFound(detail=f"Aisle ID {id} Not Found")

        mutated_data = aisle.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_aisle, key, value)

        setattr(existing_aisle, "update_dt", datetime.utcnow())

        session.add(existing_aisle)
        session.commit()
        session.refresh(existing_aisle)

        return existing_aisle

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_aisle(id: int, session: Session = Depends(get_session)):
    """
    Delete an aisle with the given id.

    **Args**:
    - id: The id of the aisle to be deleted.

    **Returns**:
    - None: If the aisle is deleted successfully.

    **Raises**:
    - HTTPException: If the aisle is not found.
    """
    aisle = session.get(Aisle, id)

    if aisle:
        session.delete(aisle)
        session.commit()
        return HTTPException(
            status_code=204, detail=f"Aisle ID {id} Deleted " f"Successfully"
        )

    raise NotFound(detail=f"Aisle ID {id} Not Found")
