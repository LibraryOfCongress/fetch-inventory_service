# /code/app/routers/non_tray_item_retrieval_events.py - REFACRORED TO SQLALCHEMY V2

from datetime import datetime, timezone

from fastapi.responses import Response
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now


from app.database.session import get_session
from app.filter_params import SortParams
from app.sorting import BaseSorter
from app.models.non_tray_item_retrieval_events import NonTrayItemRetrievalEvent
from app.schemas.non_tray_tem_retrieval_events import (
    NonTrayItemRetrievalEventInput,
    NonTrayItemRetrievalEventUpdateInput,
    NonTrayItemRetrievalEventListOutput,
    NonTrayItemRetrievalEventDetailOutput,
)
from app.config.exceptions import NotFound


from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/non-tray-item-retrieval-events",
    tags=["Non tray item retrieval events"],
    dependencies=[Depends(RequiresPermission("can_access_reports"))],
)


@router.get("/", response_model=Page[NonTrayItemRetrievalEventListOutput])
def get_non_tray_item_retrieval_events(
    session: Session = Depends(get_session), sort_params: SortParams = Depends()
):
    """
    Retrieve a list of all non tray item retrieval events.
    """
    # Create a query to retrieve all Groups
    query = select(NonTrayItemRetrievalEvent)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(NonTrayItemRetrievalEvent)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=NonTrayItemRetrievalEventDetailOutput)
def get_non_tray_item_retrieval_event_detail(
    id: int,
    session: Session = Depends(get_session),
):
    """
    Retrieve the details of a non tray item retrieval event by its ID.
    """
    non_tray_item_retrieval_event = session.get(NonTrayItemRetrievalEvent, id)

    if not non_tray_item_retrieval_event:
        raise NotFound(detail=f"Non Tray Item Retrieval Event ID {id} Not Found")

    return non_tray_item_retrieval_event


@router.post("/", response_model=NonTrayItemRetrievalEventDetailOutput, status_code=201)
def create_non_tray_item_retrieval_event(
    non_tray_item_retrieval_event: NonTrayItemRetrievalEventInput,
    session: Session = Depends(get_session),
):
    """
    Create a new non tray item retrieval event.
    """
    new_non_tray_item_retrieval_event = NonTrayItemRetrievalEvent(
        **non_tray_item_retrieval_event.model_dump()
    )
    session.add(new_non_tray_item_retrieval_event)
    session.commit()
    session.refresh(new_non_tray_item_retrieval_event)

    return new_non_tray_item_retrieval_event


@router.patch("/{id}", response_model=NonTrayItemRetrievalEventDetailOutput)
def update_non_tray_item_retrieval_event(
    id: int,
    non_tray_item_retrieval_event: NonTrayItemRetrievalEventUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a non tray item retrieval event by its ID.
    """
    existing_non_tray_item_retrieval_event = session.get(NonTrayItemRetrievalEvent, id)

    if not existing_non_tray_item_retrieval_event:
        raise NotFound(detail=f"Non Tray Item Retrieval Event ID {id} Not Found")

    mutated_data = non_tray_item_retrieval_event.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_non_tray_item_retrieval_event, key, value)

    setattr(existing_non_tray_item_retrieval_event, "update_dt", datetime.now(timezone.utc))

    session.add(existing_non_tray_item_retrieval_event)
    session.commit()
    session.refresh(existing_non_tray_item_retrieval_event)

    return existing_non_tray_item_retrieval_event


@router.delete("/{id}")
def delete_non_tray_item_retrieval_event(
    id: int, session: Session = Depends(get_session)
):
    """
    Delete a non tray item retrieval event by its ID.
    """
    non_tray_item_retrieval_event = session.get(NonTrayItemRetrievalEvent, id)

    if non_tray_item_retrieval_event:
        session.delete(non_tray_item_retrieval_event)
        session.commit()
        return Response(status_code=204)

    raise NotFound(detail=f"Non Tray Item Retrieval Event ID {id} Not Found")
