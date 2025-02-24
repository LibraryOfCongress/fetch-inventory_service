from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from typing import Optional

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.aisles import Aisle
from app.models.aisle_numbers import AisleNumber
from app.models.modules import Module
from app.schemas.aisles import (
    AisleInput,
    AisleUpdateInput,
    AisleListOutput,
    AisleDetailWriteOutput,
    AisleDetailReadOutput,
)
from app.config.exceptions import NotFound, ValidationException, InternalServerError

import traceback

from app.sorting import BaseSorter

router = APIRouter(
    prefix="/aisles",
    tags=["aisles"],
)


@router.get("/", response_model=Page[AisleListOutput])
def get_aisle_list(
    session: Session = Depends(get_session),
    module_number: Optional[str] = None,
    building_id: Optional[int] = None,
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get a paginated list of aisles.

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.

    **Returns**:
    - Aisle List Output: The paginated list of aisles.
    """
    query = select(Aisle).distinct()

    if module_number:
        query = query.join(Module, Aisle.module_id == Module.id).where(
            Module.module_number == module_number
        )
        if building_id:
            query.filter(Module.building_id == building_id)
    elif building_id:
        query.join(Module, Aisle.module_id == Module.id).where(
            Module.building_id == building_id
        )

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = BaseSorter(Aisle)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


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
        # Check if aisle # or aisle_number_id
        aisle_number = aisle_input.aisle_number
        aisle_number_id = aisle_input.aisle_number_id
        mutated_data = aisle_input.model_dump(exclude="aisle_number")
        if not aisle_number_id and not aisle_number:
            raise ValidationException(
                detail=f"aisle_number_id OR aisle_number required"
            )
        elif aisle_number and not aisle_number_id:
            # get aisle_number_id from aisle number
            aisle_num_object = (
                session.query(AisleNumber)
                .filter(AisleNumber.number == aisle_number)
                .first()
            )
            if not aisle_num_object:
                raise ValidationException(
                    detail=f"No aisle_number entity exists for aisle number {aisle_number}"
                )
            mutated_data["aisle_number_id"] = aisle_num_object.id

        # Create a new Aisle object
        # new_aisle = Aisle(**aisle_input.model_dump())
        new_aisle = Aisle(**mutated_data)
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

        setattr(existing_aisle, "update_dt", datetime.now(timezone.utc))

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
            status_code=204, detail=f"Aisle ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Aisle ID {id} Not Found")
