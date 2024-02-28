import uuid

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.barcodes import Barcode
from app.schemas.barcodes import (
    BarcodeInput,
    BarcodeUpdateInput,
    BarcodeListOutput,
    BarcodeDetailWriteOutput,
    BarcodeDetailReadOutput,
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

    raise HTTPException(status_code=404)


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
    new_barcode = Barcode(**barcode_input.model_dump())
    session.add(new_barcode)
    session.commit()
    session.refresh(new_barcode)
    return new_barcode


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
    existing_barcode = session.get(Barcode, id)

    if not existing_barcode:
        raise HTTPException(status_code=404)

    mutated_data = barcode.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_barcode, key, value)

    setattr(existing_barcode, "update_dt", datetime.utcnow())

    session.add(existing_barcode)
    session.commit()
    session.refresh(existing_barcode)

    return existing_barcode


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
        return HTTPException(status_code=204)

    raise HTTPException(status_code=404)
