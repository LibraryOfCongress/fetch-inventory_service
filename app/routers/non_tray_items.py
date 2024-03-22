from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.non_tray_items import NonTrayItem
from app.models.barcodes import Barcode
from app.schemas.non_tray_items import (
    NonTrayItemInput,
    NonTrayItemUpdateInput,
    NonTrayItemListOutput,
    NonTrayItemDetailWriteOutput,
    NonTrayItemDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)


router = APIRouter(
    prefix="/non_tray_items",
    tags=["non tray items"],
)


@router.get("/", response_model=Page[NonTrayItemListOutput])
def get_non_tray_item_list(session: Session = Depends(get_session)) -> list:
    """
    Get a paginated list of non tray items from the database
    """
    # Create a query to select all non tray items from the database
    return paginate(session, select(NonTrayItem))


@router.get("/{id}", response_model=NonTrayItemDetailReadOutput)
def get_non_tray_item_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a non_tray_item by its ID
    """
    non_tray_item = session.get(NonTrayItem, id)

    if non_tray_item:
        return non_tray_item

    raise NotFound(detail=f"Non Tray Item ID {id} Not Found")


@router.get("/barcode/{value}", response_model=NonTrayItemDetailReadOutput)
def get_non_tray_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a non-tray using a barcode value

    **Parameters:**
    - value (str): The value of the barcode to retrieve.
    """
    statement = select(NonTrayItem).join(Barcode).where(Barcode.value == value)
    non_tray = session.exec(statement).first()
    if not non_tray:
        raise NotFound()
    return non_tray


@router.post("/", response_model=NonTrayItemDetailWriteOutput, status_code=201)
def create_non_tray_item(
    item_input: NonTrayItemInput, session: Session = Depends(get_session)
):
    """
    Create a new non_tray_item record
    """

    try:
        # Create a new non_tray_item
        new_non_tray_item = NonTrayItem(**item_input.model_dump())
        session.add(new_non_tray_item)
        session.commit()
        session.refresh(new_non_tray_item)

        return new_non_tray_item

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=NonTrayItemDetailWriteOutput)
def update_non_tray_item(
    id: int,
    non_tray_item: NonTrayItemUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a non_tray_item record in the database
    """

    try:
        # Get the existing non_tray_item record from the database
        existing_non_tray_item = session.get(NonTrayItem, id)

        # Check if the non_tray_item record exists
        if not existing_non_tray_item:
            raise NotFound(detail=f"Non Tray Item ID {id} Not Found")

        # Update the non_tray_item record with the mutated data
        mutated_data = non_tray_item.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_non_tray_item, key, value)
        setattr(existing_non_tray_item, "update_dt", datetime.utcnow())

        # Commit the changes to the database
        session.add(existing_non_tray_item)
        session.commit()
        session.refresh(existing_non_tray_item)

        return existing_non_tray_item

    except Exception as e:
        raise InternalServerError(detail=f"{e}")

@router.delete("/{id}")
def delete_non_tray_item(id: int, session: Session = Depends(get_session)):
    """
    Delete a non_tray_item by its ID
    """
    non_tray_item = session.get(NonTrayItem, id)

    if non_tray_item:
        session.delete(non_tray_item)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Non Tray Item ID {id} Deleted "
                                    f"Successfully"
        )


    raise NotFound(detail=f"Non Tray Item ID {id} Not Found")
