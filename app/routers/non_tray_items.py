from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.non_tray_items import NonTrayItem
from app.schemas.non_tray_items import (
    NonTrayItemInput,
    NonTrayItemUpdateInput,
    NonTrayItemListOutput,
    NonTrayItemDetailWriteOutput,
    NonTrayItemDetailReadOutput,
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
    else:
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/", response_model=NonTrayItemDetailWriteOutput, status_code=201)
def create_non_tray_item(item_input: NonTrayItemInput, session: Session = Depends(get_session)):
    """
    Create a new non_tray_item record
    """

    # Create a new non_tray_item
    new_non_tray_item = NonTrayItem(**item_input.model_dump())
    session.add(new_non_tray_item)
    session.commit()
    session.refresh(new_non_tray_item)
    return new_non_tray_item


@router.patch("/{id}", response_model=NonTrayItemDetailWriteOutput)
def update_non_tray_item(
    id: int, non_tray_item: NonTrayItemUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a non_tray_item record in the database
    """
    # Get the existing non_tray_item record from the database
    existing_non_tray_item = session.get(NonTrayItem, id)

    # Check if the non_tray_item record exists
    if not existing_non_tray_item:
        raise HTTPException(status_code=404, detail="Not Found")

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


@router.delete("/{id}")
def delete_non_tray_item(id: int, session: Session = Depends(get_session)):
    """
    Delete a non_tray_item by its ID
    """
    non_tray_item = session.get(NonTrayItem, id)

    if non_tray_item:
        session.delete(non_tray_item)
        session.commit()
        return HTTPException(status_code=204)
    else:
        raise HTTPException(status_code=404)
