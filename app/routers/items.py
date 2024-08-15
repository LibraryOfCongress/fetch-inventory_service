from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.barcodes import Barcode
from app.models.items import Item
from app.schemas.items import (
    ItemInput,
    ItemUpdateInput,
    ItemListOutput,
    ItemDetailWriteOutput,
    ItemDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)


router = APIRouter(
    prefix="/items",
    tags=["items"],
)


@router.get("/", response_model=Page[ItemListOutput])
def get_item_list(
    session: Session = Depends(get_session),
    owner_id: int = Query(default=None),
    size_class_id: int = Query(default=None),
    media_type_id: int = Query(default=None),
    from_dt: datetime = Query(default=None),
    to_dt: datetime = Query(default=None),
) -> list:
    """
    Retrieve a paginated list of items from the database.

    **Returns:**
    - Item List Output: The paginated list of items.
    """
    # Create a query to select all items from the database
    query = select(Item).distinct()

    if owner_id:
        query = query.where(Item.owner_id == owner_id)
    if size_class_id:
        query = query.where(Item.size_class_id == size_class_id)
    if media_type_id:
        query = query.where(Item.media_type_id == media_type_id)
    if from_dt:
        query = query.where(Item.accession_dt >= from_dt)
    if to_dt:
        query = query.where(Item.accession_dt <= to_dt)

    return paginate(session, query)


@router.get("/{id}", response_model=ItemDetailReadOutput)
def get_item_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve details of a specific item by ID.

    **Args:**
    - id (int): The ID of the item to retrieve.

    **Returns:**
    - Item Detail Read Output: Details of the item.

    **Raises:**
    - HTTPException: If the item is not found.
    """
    item = session.get(Item, id)
    if item:
        return item

    raise NotFound(detail=f"Item ID {id} Not Found")


@router.get("/barcode/{value}", response_model=ItemDetailReadOutput)
def get_item_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a item using a barcode value

    **Parameters:**
    - value (str): The value of the barcode to retrieve.
    """
    if not value:
        raise ValidationException(detail="Item barcode value is required")

    statement = select(Item).join(Barcode).where(Barcode.value == value)
    item = session.exec(statement).first()
    if not item:
        raise NotFound(detail=f"Item with barcode value {value} not found")
    return item


@router.post("/", response_model=ItemDetailWriteOutput, status_code=201)
def create_item(item_input: ItemInput, session: Session = Depends(get_session)):
    """
    Create a new item in the database.

    **Parameters:**
    - Item Input: model containing item details to be added.

    **Returns:**
    - Item Detail Write Output: Newly created item details.
    """
    try:
        # Create a new item
        new_item = Item(**item_input.model_dump())
        new_item.withdrawal_dt = None
        # accession is how items are created. Set accession_dt
        if not new_item.accession_dt:
            new_item.accession_dt = datetime.utcnow()

        # check if existing withdrawn item with this barcode
        previous_item = session.exec(select(Item).where(
            Item.barcode_id == new_item.barcode_id
        )).first()
        if previous_item:
            # use existing, and patch values
            for field, value in new_item.dict(exclude={'id'}).items():
                setattr(previous_item, field, value)
            new_item = previous_item
            new_item.scanned_for_verification = False
            new_item.scanned_for_refile_queue = False
            barcode = select(Barcode).where(
                Barcode.id == new_item.barcode_id
            )
            barcode.withdrawn = False
            session.add(barcode)
        session.add(new_item)
        session.commit()
        session.refresh(new_item)

        return new_item

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=ItemDetailWriteOutput)
def update_item(
    id: int, item: ItemUpdateInput, session: Session = Depends(get_session)
):
    """
    Update item details in the database.

    **Args:**
    - id: The ID of the item to update.
    - Item Update Input: The updated item data.

    **Returns:**
    - Item Detail Write Output: The updated item details.
    """
    try:
        # Get the existing item record from the database
        existing_item = session.get(Item, id)

        # Check if the item record exists
        if not existing_item:
            raise NotFound(detail=f"Item ID {id} Not Found")

        # Update the item record with the mutated data
        mutated_data = item.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_item, key, value)
        setattr(existing_item, "update_dt", datetime.utcnow())

        # Commit the changes to the database
        session.add(existing_item)
        session.commit()
        session.refresh(existing_item)

        return existing_item

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_item(id: int, session: Session = Depends(get_session)):
    """
    Delete an item by its ID.

    **Parameters:**
    - id: the ID of the item to be deleted

    **Returns:**
    - HTTPException: status code 204 if item is successfully deleted, status code 404 if item not found
    """

    item = session.get(Item, id)

    if item:
        session.delete(item)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Item ID {id} Deleted " f"Successfully"
        )

    raise NotFound(detail=f"Item ID {id} Not Found")
