from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime, timezone
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
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
from app.utilities import get_sorted_query

router = APIRouter(
    prefix="/barcodes",
    tags=["barcodes"],
)


@router.get("/types", response_model=Page[BarcodeTypesListOutput])
def get_barcode_types_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a list of barcode types.

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    -Barcode Types List Output: The paginated list of barcode types.
    """
    # Create a query to select all barcode types
    query = select(BarcodeType).distinct()

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(BarcodeType, query, sort_params)

    return paginate(session, query)


@router.get("/types/{id}", response_model=BarcodeTypesDetailReadOutput)
def get_barcode_types_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve details of a specific barcode type.

    **Parameters:**
    - id: The ID of the barcode type to retrieve.

    **Returns:**
    - Barcode Types Detail Read Output: The details of the barcode type.

    **Raises:**
    - HTTPException: If the barcode type with the specified ID is not found.
    """
    # Retrieve the barcode type from the session
    barcode_types = session.get(BarcodeType, id)

    if barcode_types:
        return barcode_types

    raise NotFound(detail=f"Barcode Type ID {id} Not Found")


@router.post("/types", response_model=BarcodeTypesDetailWriteOutput, status_code=201)
def create_barcode_types(
    barcode_types_input: BarcodeTypesInput, session: Session = Depends(get_session)
) -> BarcodeType:
    """
    Creates a new barcode type using the provided input data.

    **Parameters:**
    - Barcode Types Input: The input data for the barcode types.

    **Returns:**
    - Barcode Types: The newly created barcode type.
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


@router.patch("/types/{id}", response_model=BarcodeTypesDetailWriteOutput)
def update_barcode_types(
    id: int, barcode_types: BarcodeTypesInput, session: Session = Depends(get_session)
):
    """
    Update barcode type details.

    **Parameters:**
    - id: The ID of the barcode type to update.

    **Returns:**
    - Barcode Types Detail Write Output: The updated barcode type.
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
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/types/{id}")
def delete_barcode_types(id: int, session: Session = Depends(get_session)):
    """
    Delete barcode types by id.

    **Parameters:**
    - id: The id of the barcode types to delete.

    **Raises:**
    - HTTPException: If the barcode types with the given id does not exist.
    """
    # Get the barcode types from the session by id
    barcode_types = session.get(BarcodeType, id)

    if barcode_types:
        session.delete(barcode_types)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Barcode Type ID {id} Deleted "
                                    f"Successfully"
            )

    raise NotFound(detail=f"Barcode Type ID {id} Not Found")
