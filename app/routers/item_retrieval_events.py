from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select


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


router = APIRouter(
    prefix="/item-retrieval-events",
    tags=["Item retrieval events"],
)


@router.get("/", response_model=Page[ItemRetrievalEventListOutput])
def get_item_retrieval_events(
    session: Session = Depends(get_session), sort_params: SortParams = Depends()
):
    """
    Retrieve a list of all item retrieval evens.

    **Args:**
    - sort_params: The sorting parameters.

    **Returns:**
    - Item Retrieval Event List Output: A paginated list of Item Retrieval Events.
    """
    # Create a query to retrieve all Groups
    query = select(ItemRetrievalEvent).distinct()

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

    **Args:**
    - id: The ID of the item retrieval even to retrieve.

    **Returns:**
    - Item Retrieval Event Detail Output: The details of the item retrieval even.
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

    **Args:**
    - Item Retrieval Event Input: The input data for creating the
    item retrieval even.

    **Returns:**
    - Item Retrieval Event Detail Output: The created item retrieval even.

    **Raises:**
    - HTTPException: If there is an integrity error during the creation of the
    item retrieval even.
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

    **Args:**
    - id: The ID of the item retrieval even to update.
    - Item Retrieval Event Update Input: The updated item retrieval even data.

    **Returns:**
    - Item Retrieval Event Detail Output: The updated item retrieval even.

    **Raises:**
    - HTTPException: If the item retrieval even is not found or if an error occurs during the update.
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

    **Args:**
    - id: The ID of the item retrieval event to delete.

    **Returns:**
    - None: If the item retrieval event is deleted successfully.

    **Raises:**
    - HTTPException: If the item retrieval event is not found.
    """
    item_retrieval_event = session.get(ItemRetrievalEvent, id)

    if item_retrieval_event:
        session.delete(item_retrieval_event)
        session.commit()
        return HTTPException(
            status_code=204, detail=f"Item Retrieval Event ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Item Retrieval Event ID {id} Not Found")
