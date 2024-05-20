import uuid, re

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from typing import List
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.barcodes import Barcode
from app.models.barcode_types import BarcodeType
from app.schemas.barcodes import (
    BarcodeInput,
    BarcodeUpdateInput,
    BarcodeListOutput,
    BarcodeDetailWriteOutput,
    BarcodeDetailReadOutput,
    BarcodeMutationInput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

router = APIRouter(
    prefix="/barcodes",
    tags=["barcodes"],
)


@router.get("/", response_model=Page[BarcodeListOutput])
def get_barcode_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a list of barcodes from the database.

    **Returns:**
    - list: A list of barcodes.
    """
    # Create a query to retrieve all barcodes
    return paginate(session, select(Barcode))


@router.get("/{id}", response_model=BarcodeDetailReadOutput)
def get_barcode_detail(id: uuid.UUID, session: Session = Depends(get_session)):
    """
    Retrieve barcode details by ID.

    **Parameters:**
    - id (int): The ID of the barcode to retrieve.

    **Returns:**
    - Barcode Detail Read Output: The barcode details.

    **Raises:**
    - HTTPException: If the barcode is not found.
    """
    # Retrieve the barcode from the database by ID
    barcode = session.get(Barcode, id)

    if barcode:
        return barcode

    raise NotFound(detail=f"Barcode ID {id} Not Found")


@router.get("/value/{value}", response_model=BarcodeDetailReadOutput)
def get_barcode_by_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve barcode details by its value

    **Parameters:**
    - value (str): The value of the barcode to retrieve.

    **Returns:**
    - Barcode Detail Read Output: The barcode details.

    **Raises:**
    - HTTPException: If the barcode is not found.
    """
    statement = select(Barcode).where(Barcode.value == value)
    barcode = session.exec(statement).first()
    if not barcode:
        raise NotFound()
    return barcode



@router.post("/", response_model=BarcodeDetailWriteOutput, status_code=201)
def create_barcode(
    barcode_input: BarcodeInput, session: Session = Depends(get_session)
) -> Barcode:
    """
    Create a new barcode.

    **Args:**
    - Barcode Input: The input data for creating a barcode.

    **Returns:**
    - Barcode: The newly created barcode.
    """
    try:
        barcode_type_string = barcode_input.type
        barcode_type = session.exec(
            select(BarcodeType).where(BarcodeType.name == barcode_type_string)
        ).first()
        if not barcode_type:
            raise NotFound(detail=f"Barcode type '{barcode_type_string}' not found.")
        else:
            mutated_barcode_input = barcode_input.dict()
            mutated_barcode_input['type_id'] = barcode_type.id
            # Use muttion input to avoid missing type_id validation
            mutated_barcode_input = BarcodeMutationInput(**mutated_barcode_input)

        # validate value against barcode_type allowed_pattern
        if not re.fullmatch(barcode_type.allowed_pattern, barcode_input.value):
            raise ValidationException(detail=f"Barcode value is invalid for {barcode_type.name} barcode rules.")

        new_barcode = Barcode(**mutated_barcode_input.model_dump(exclude={'type'}))
        session.add(new_barcode)
        session.commit()
        session.refresh(new_barcode)

        return new_barcode

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=BarcodeDetailWriteOutput)
def update_barcode(
    id: uuid.UUID, barcode: BarcodeUpdateInput, session: Session = Depends(get_session)
):
    """
    Update barcode details.

    **Parameters:**
    - id (int): The ID of the barcode to retrieve.
    - Barcode Update Input: The updated barcode details.

    **Returns:**
    - Barcode Update Input: The barcode details.

    **Raises:**
    - HTTPException: If the barcode is not found.
    """
    try:
        # First check if new barcode type and if exists
        new_barcode_type = None
        mutated_barcode_type_id = None
        if barcode.type:
            new_barcode_type = session.exec(
                select(BarcodeType).where(BarcodeType.name == barcode.type)
            ).first()
            if not new_barcode_type:
                raise NotFound(detail=f"Barcode type {barcode.type} not found.")
            else:
                # barcode['type_id'] = new_barcode_type.id
                mutated_barcode_type_id = new_barcode_type.id

        existing_barcode = session.get(Barcode, id)

        if not existing_barcode:
            raise NotFound(detail=f"Barcode ID {id} Not Found")

        if new_barcode_type:
            # use new allowed pattern to validate
            if barcode.value:
                # Validate against incoming value
                if not re.fullmatch(new_barcode_type.allowed_pattern, barcode.value):
                    raise ValidationException(detail=f"Barcode value is invalid for {new_barcode_type.name} barcode rules.")
            else:
                # Validate existing value
                if not re.fullmatch(new_barcode_type.allowed_pattern, existing_barcode.value):
                    raise ValidationException(detail=f"Barcode type {new_barcode_type.name} would make existing barcode value invalid.")
        else:
            # use existing allowed pattern to validate
            existing_barcode_type = session.exec(
                select(BarcodeType).where(BarcodeType.id == existing_barcode.type_id)
            ).first()
            if barcode.value:
                # Validate incoming against existing allowed_pattern
                if not re.fullmatch(existing_barcode_type.allowed_pattern, barcode.value):
                    raise ValidationException(detail=f"New Barcode value is invalid for {existing_barcode_type.name} barcode rules.")
            # Else neither type or barcode value changed, nothing to validate

        mutated_data = barcode.model_dump(
            exclude={'type'},
            exclude_unset=True
        )

        if mutated_barcode_type_id:
            mutated_data['type_id'] = mutated_barcode_type_id

        for key, value in mutated_data.items():
            setattr(existing_barcode, key, value)

        setattr(existing_barcode, "update_dt", datetime.utcnow())

        session.add(existing_barcode)
        session.commit()
        session.refresh(existing_barcode)

        return existing_barcode
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_barcode(id: uuid.UUID, session: Session = Depends(get_session)):
    """
    Deletes a barcode by its ID.

    **Parameters:**
    - id (int): The ID of the barcode to delete.

    **Returns:**
    - None

    **Raises:**
    - HTTPException: If the barcode with the given ID is not found.
    """
    # Get the barcode with the given ID from the session
    barcode = session.get(Barcode, id)

    if barcode:
        session.delete(barcode)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Barcode ID {id} Deleted "
                                    f"Successfully"
        )

    raise NotFound(detail=f"Barcode ID {id} Not Found")
