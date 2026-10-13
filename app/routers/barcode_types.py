# /code/app/routers/barcodes.py - REFACRORED TO SQLALCHEMY V2

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.barcode_types import BarcodeType
from app.schemas.barcode_types import (
    BarcodeTypesInput,
    BarcodeTypesListOutput,
    BarcodeTypesDetailWriteOutput,
    BarcodeTypesDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/barcodes",
    tags=["barcodes"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/types", response_model=Page[BarcodeTypesListOutput])
def get_barcode_types_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a list of barcode types.
    """
    # Create a query to select all barcode types
    query = select(BarcodeType)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = BaseSorter(BarcodeType)
        query = sorter.apply_sorting(query, sort_params)

    # CRITICAL FIX: Paginate now takes only the query object
    return paginate(session, query)


@router.get("/types/{id}", response_model=BarcodeTypesDetailReadOutput)
def get_barcode_types_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve details of a specific barcode type.
    """
    # Retrieve the barcode type from the session
    barcode_types = session.get(BarcodeType, id)

    if barcode_types:
        return barcode_types

    raise NotFound(detail=f"Barcode Type ID {id} Not Found")


@router.post("/types", response_model=BarcodeTypesDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def create_barcode_types(
    barcode_types_input: BarcodeTypesInput, session: Session = Depends(get_session)
) -> BarcodeType:
    """
    Creates a new barcode type using the provided input data.
    """
    try:
        # Create a new instance of BarcodeTypes using the input data
        new_barcode_types = BarcodeType(**barcode_types_input.model_dump())
        session.add(new_barcode_types)
        session.commit()
        session.refresh(new_barcode_types)

        return new_barcode_types

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/types/{id}", response_model=BarcodeTypesDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def update_barcode_types(
    id: int, barcode_types: BarcodeTypesInput, session: Session = Depends(get_session)
):
    """
    Update barcode type details.
    """
    try:
        existing_barcode_types = session.get(BarcodeType, id)

        if not existing_barcode_types:
            raise NotFound(detail=f"Barcode Type ID {id} Not Found")


        mutated_data = barcode_types.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_barcode_types, key, value)

        setattr(existing_barcode_types, "update_dt", datetime.now(timezone.utc))

        session.add(existing_barcode_types)
        session.commit()
        session.refresh(existing_barcode_types)

        return existing_barcode_types
    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/types/{id}", dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def delete_barcode_types(id: int, session: Session = Depends(get_session)):
    """
    Delete barcode types by id.
    """
    # Get the barcode types from the session by id
    barcode_types = session.get(BarcodeType, id)

    if barcode_types:
        session.delete(barcode_types)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Barcode Type ID {id} Not Found")