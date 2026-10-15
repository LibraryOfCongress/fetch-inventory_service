# /code/app/routers/barcodes.py - FINAL CORRECTED V2
import re

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from typing import Optional

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.barcodes import Barcode
from app.models.barcode_types import BarcodeType
from app.schemas.barcodes import (
    BarcodeInput,
    BarcodeUpdateInput,
    BarcodeListOutput,
    BarcodeDetailWriteOutput,
    BarcodeDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
    BadRequest
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/barcodes",
    tags=["barcodes"],
    # Authenticated-only at the router level; writes carry the manage permission
    # per-endpoint so GETs (e.g. the Item Lookup tool) aren't gated by admin perms.
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/", response_model=Page[BarcodeListOutput])
def get_barcode_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Barcode Value"),
) -> list:
    """
    Get a paginated list of barcodes.
    """
    query = select(Barcode)

    if search:
        query = query.where(Barcode.value.icontains(search))

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(Barcode)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/value/{value}", response_model=BarcodeDetailReadOutput)
def get_barcode_by_value(
    value: str,
    session: Session = Depends(get_session)
):
    """
    Get a specific barcode by its value string.
    Used by frontend verification logic.
    """
    # V2 FIX: session.execute(select(...)).scalars().first()
    barcode = session.execute(
        select(Barcode).where(Barcode.value == value)
    ).scalars().first()

    if barcode:
        return barcode

    raise NotFound(detail=f"Barcode value '{value}' Not Found")


@router.get("/{id}", response_model=BarcodeDetailReadOutput)
def get_barcode_detail(id: str, session: Session = Depends(get_session)):
    """
    Retrieve details of a specific barcode by UUID.
    """
    # session.get handles UUIDs correctly if the model PK is UUID
    barcode = session.get(Barcode, id)

    if barcode:
        return barcode

    raise NotFound(detail=f"Barcode ID {id} Not Found")



@router.post("/", response_model=BarcodeDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_access_accession", "can_access_verification", any_of=True))])
def create_barcode(
    barcode_input: BarcodeInput, session: Session = Depends(get_session)
) -> Barcode:
    """
    Creates a new barcode.
    Accepts 'type' as a string (e.g., 'Tray', 'Item') and resolves it to a type_id.
    """
    try:
        # 1. Check if barcode already exists
        existing_barcode = session.execute(
            select(Barcode).where(Barcode.value == barcode_input.value)
        ).scalars().first()

        if existing_barcode:
            raise ValidationException(detail=f"Barcode '{barcode_input.value}' already exists.")

        # 2. Resolve the Type String to an ID
        barcode_type = session.execute(
            select(BarcodeType).where(BarcodeType.name == barcode_input.type)
        ).scalars().first()

        if not barcode_type:
            raise BadRequest(detail=f"Barcode Type '{barcode_input.type}' not found.")

        # 2a. Validate Barcode Pattern
        if barcode_type.allowed_pattern:
            if not re.fullmatch(barcode_type.allowed_pattern, barcode_input.value):
                raise ValidationException(
                    detail=f"Barcode '{barcode_input.value}' does not match the required pattern for type '{barcode_input.type}'."
                )

        # 3. Create the Barcode
        # We manually map the input fields to the model because input has 'type' (str)
        # but model needs 'type_id' (int)
        new_barcode = Barcode(
            value=barcode_input.value,
            type_id=barcode_type.id,
            withdrawn=False, # Default
            # IDs and Dates handled by DB defaults/Base model
        )

        session.add(new_barcode)
        session.commit()
        session.refresh(new_barcode)

        return new_barcode

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=BarcodeDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_access_accession", "can_access_verification", any_of=True))])
def update_barcode(
    id: str, barcode_input: BarcodeUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a barcode record.
    """
    try:
        existing_barcode = session.get(Barcode, id)

        if not existing_barcode:
            raise NotFound(detail=f"Barcode ID {id} Not Found")

        mutated_data = barcode_input.model_dump(exclude_unset=True)

        # Handle type string update if present
        if "type" in mutated_data:
            type_name = mutated_data.pop("type")
            barcode_type = session.execute(
                select(BarcodeType).where(BarcodeType.name == type_name)
            ).scalars().first()

            if not barcode_type:
                 raise BadRequest(detail=f"Barcode Type '{type_name}' not found.")

            existing_barcode.type_id = barcode_type.id

        for key, value in mutated_data.items():
            setattr(existing_barcode, key, value)

        setattr(existing_barcode, "update_dt", datetime.now(timezone.utc))

        session.add(existing_barcode)
        session.commit()
        session.refresh(existing_barcode)

        return existing_barcode
    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", status_code=204, dependencies=[Depends(RequiresPermission("can_access_accession", "can_access_verification", any_of=True))])
def delete_barcode(id: str, session: Session = Depends(get_session)):
    """
    Delete a barcode by its ID.
    """
    barcode = session.get(Barcode, id)

    if barcode:
        session.delete(barcode)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Barcode ID {id} Not Found")
