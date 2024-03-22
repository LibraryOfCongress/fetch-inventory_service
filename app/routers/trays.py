from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.trays import Tray
from app.models.barcodes import Barcode
from app.schemas.trays import (
    TrayInput,
    TrayUpdateInput,
    TrayListOutput,
    TrayDetailWriteOutput,
    TrayDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)


router = APIRouter(
    prefix="/trays",
    tags=["trays"],
)


@router.get("/", response_model=Page[TrayListOutput])
def get_tray_list(session: Session = Depends(get_session)) -> list:
    """
    Get a paginated list of trays from the database
    """
    # Create a query to select all trays from the database
    return paginate(session, select(Tray))


@router.get("/{id}", response_model=TrayDetailReadOutput)
def get_tray_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a tray by its ID
    """
    tray = session.get(Tray, id)

    if tray:
        return tray

    raise NotFound(detail=f"Tray ID {id} Not Found")


@router.get("/barcode/{value}", response_model=TrayDetailReadOutput)
def get_tray_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a tray using a barcode value

    **Parameters:**
    - value (str): The value of the barcode to retrieve.
    """
    statement = select(Tray).join(Barcode).where(Barcode.value == value)
    tray = session.exec(statement).first()
    if not tray:
        raise NotFound()
    return tray


@router.post("/", response_model=TrayDetailWriteOutput, status_code=201)
def create_tray(tray_input: TrayInput, session: Session = Depends(get_session)):
    """
    Create a new tray record
    """
    try:
        # Create a new tray
        new_tray = Tray(**tray_input.model_dump())
        session.add(new_tray)
        session.commit()
        session.refresh(new_tray)

        return new_tray

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=TrayDetailWriteOutput)
def update_tray(
    id: int, tray: TrayUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a tray record in the database
    """
    try:
        # Get the existing tray record from the database
        existing_tray = session.get(Tray, id)

        # Check if the tray record exists
        if not existing_tray:
            raise NotFound(detail=f"Tray ID {id} Not Found")

        # Update the tray record with the mutated data
        mutated_data = tray.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_tray, key, value)
        setattr(existing_tray, "update_dt", datetime.utcnow())

        # Commit the changes to the database
        session.add(existing_tray)
        session.commit()
        session.refresh(existing_tray)

        return existing_tray

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_tray(id: int, session: Session = Depends(get_session)):
    """
    Delete a tray by its ID
    """
    tray = session.get(Tray, id)

    if tray:
        session.delete(tray)
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Tray id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Tray ID {id} Not Found")
