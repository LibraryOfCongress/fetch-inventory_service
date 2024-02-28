from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.items import Item
from app.schemas.items import (
    ItemInput,
    ItemUpdateInput,
    ItemListOutput,
    ItemDetailWriteOutput,
    ItemDetailReadOutput,
)


router = APIRouter(
    prefix="/items",
    tags=["items"],
)


@router.get("/", response_model=Page[ItemListOutput])
def get_item_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of items from the database.

    **Returns:**
    - Item List Output: The paginated list of items.
    """
    # Create a query to select all items from the database
    return paginate(session, select(Item))


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
    else:
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/", response_model=ItemDetailWriteOutput, status_code=201)
def create_item(item_input: ItemInput, session: Session = Depends(get_session)):
    """
    Create a new item in the database.

    **Parameters:**
    - Item Input: model containing item details to be added.

    **Returns:**
    - Item Detail Write Output: Newly created item details.
    """
    # Create a new item
    new_item = Item(**item_input.model_dump())
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    return new_item


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
    # Get the existing item record from the database
    existing_item = session.get(Item, id)

    # Check if the item record exists
    if not existing_item:
        raise HTTPException(status_code=404, detail="Not Found")

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
        return HTTPException(status_code=204)

    raise HTTPException(status_code=404)
