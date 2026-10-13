# /code/app/routers/item_retrieval_events.py - REFACRORED TO SQLALCHEMY V2

from datetime import datetime, timezone
from typing import Optional

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now

from app.database.session import get_session
from app.filter_params import SortParams
from app.sorting import BaseSorter
from app.models.item_retrieval_events import ItemRetrievalEvent
from app.schemas.item_retrieval_events import (
    ItemRetrievalEventInput,
    ItemRetrievalEventUpdateInput,
    ItemRetrievalEventListOutput,
    ItemRetrievalEventDetailOutput,
)
from app.config.exceptions import NotFound


from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/item-retrieval-events",
    tags=["Item retrieval events"],
    dependencies=[Depends(RequiresPermission("can_access_reports"))],
)


@router.get("/", response_model=Page[ItemRetrievalEventListOutput])
def get_item_retrieval_events(
    session: Session = Depends(get_session), sort_params: SortParams = Depends()
):
    """
    Retrieve a list of all item retrieval evens.
    """
    # Create a query to retrieve all Groups
    query = select(ItemRetrievalEvent)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = BaseSorter(ItemRetrievalEvent)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=ItemRetrievalEventDetailOutput)
def get_item_retrieval_event_detail(
    id: int,
    session: Session = Depends(get_session),
):
    """
    Retrieve the details of a item retrieval even by its ID.
    """
    item_retrieval_event = session.get(ItemRetrievalEvent, id)

    if not item_retrieval_event:
        raise NotFound(detail=f"Item Retrieval Event ID {id} Not Found")

    return item_retrieval_event


@router.post("/", response_model=ItemRetrievalEventDetailOutput, status_code=201)
def create_item_retrieval_event(
    item_retrieval_event: ItemRetrievalEventInput,
    session: Session = Depends(get_session),
):
    """
    Create a new item retrieval even.
    """
    new_item_retrieval_event = ItemRetrievalEvent(**item_retrieval_event.model_dump())
    session.add(new_item_retrieval_event)
    session.commit()
    session.refresh(new_item_retrieval_event)

    return new_item_retrieval_event


@router.patch("/{id}", response_model=ItemRetrievalEventDetailOutput)
def update_item_retrieval_event(
    id: int,
    item_retrieval_event: ItemRetrievalEventUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a item retrieval even by its ID.
    """
    existing_item_retrieval_event = session.get(ItemRetrievalEvent, id)

    if not existing_item_retrieval_event:
        raise NotFound(detail=f"Item Retrieval Event ID {id} Not Found")

    mutated_data = item_retrieval_event.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_item_retrieval_event, key, value)

    setattr(existing_item_retrieval_event, "update_dt", datetime.now(timezone.utc))

    session.add(existing_item_retrieval_event)
    session.commit()
    session.refresh(existing_item_retrieval_event)

    return existing_item_retrieval_event


@router.delete("/{id}")
def delete_item_retrieval_event(id: int, session: Session = Depends(get_session)):
    """
    Delete an item retrieval event by its ID.
    """
    item_retrieval_event = session.get(ItemRetrievalEvent, id)

    if item_retrieval_event:
        session.delete(item_retrieval_event)
        session.commit()
        return Response(status_code=204)

    raise NotFound(detail=f"Item Retrieval Event ID {id} Not Found")
