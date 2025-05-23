from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from starlette import status

from app.database.session import get_session
from app.logger import inventory_logger
from app.models.barcodes import Barcode
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.pick_lists import PickList
from app.models.refile_items import RefileItem
from app.models.refile_jobs import RefileJob
from app.models.refile_non_tray_items import RefileNonTrayItem
from app.models.requests import Request

from app.schemas.refile_queue import (
    RefileQueueInput,
    RefileQueueListOutput,
    RefileQueueWriteOutput,
    TrayNestedForRefileQueue,
    NonTrayNestedForRefileQueue,
)
from app.config.exceptions import BadRequest, NotFound, ValidationException
from app.sorting import RefileQueueSorter
from app.utilities import get_refile_queue
from app.filter_params import RefileQueueParams, SortParams

router = APIRouter(
    prefix="/refile-queue",
    tags=["refile-queue"],
)


@router.get("/", response_model=Page[RefileQueueListOutput])
def get_refile_queue_list(
    params: RefileQueueParams = Depends(),
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a list of refile jobs

    **Args:**
    - scanned_queue: Whether to get the scanned queue or not
    - building_id: The ID of the building

    **Returns:**
    - Refile Job List Output: The paginated list of refile jobs
    """
    query = get_refile_queue(params)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = RefileQueueSorter(PickList)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.patch("/", response_model=RefileQueueWriteOutput)
def add_to_refile_queue(
    refile_input: RefileQueueInput, session: Session = Depends(get_session)
):
    """
    Add an item to the refile queue

    **Args:**
    - Refile Queue Input: The ID of the item to add to the refile queue.

    **Returns:**
    - Refile Queue Detail Output: The refile queue details.

    **Raises:**
    - HTTPException: If the item is not found.
    """
    lookup_barcode_value = refile_input.barcode_value
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_value:
        raise BadRequest(detail="No barcode value found in request")

    barcode = (
        session.query(Barcode).filter(Barcode.value == lookup_barcode_value).first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode value {lookup_barcode_value} not found")
    if barcode.withdrawn:
        raise ValidationException(detail="Item has already been withdrawn")

    item = session.query(Item).filter(Item.barcode_id == barcode.id).first()
    non_tray_item = (
        session.query(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id).first()
    )

    if item:
        if item.status != "Out":
            raise ValidationException(detail="Item must be in 'Out' status")
        if item.scanned_for_refile_queue:
            raise ValidationException(detail="Item is already in the refile queue")

        existing_refile_items = (
            session.query(RefileItem).filter(RefileItem.item_id == item.id).all()
        )

        if existing_refile_items:
            refile_items_id = [refile.refile_job_id for refile in existing_refile_items]
            existing_refile_job = (
                session.query(RefileJob)
                .filter(
                    RefileJob.id.in_(refile_items_id),
                    RefileJob.status != "Completed",
                )
                .first()
            )

            if existing_refile_job:
                raise ValidationException(
                    detail=f"Item already exists in an "
                    "uncompleted "
                    "refile "
                    f"Job ID: {existing_refile_job.id}"
                )
        existing_pick_list_items = (
            session.query(PickList.id)
            .join(Request, PickList.id == Request.pick_list_id)
            .filter(Request.item_id == item.id)
            .filter(PickList.status != "Completed")
            .all()
        )

        if existing_pick_list_items:
            raise ValidationException(
                detail=f"Item already exists in a uncompleted Pick List Job {existing_pick_list_items}"
            )

        item = session.get(Item, item.id)

        item.scanned_for_refile_queue = True
        item.scanned_for_refile_queue_dt = update_dt
        item.scanned_for_refile = False
        item.update_dt = update_dt

        session.add(item)

    elif non_tray_item:
        if non_tray_item.status != "Out":
            raise ValidationException(detail="Item must be in 'Out' status")
        if non_tray_item.scanned_for_refile_queue:
            raise ValidationException(detail="Item is already in the refile queue")

        existing_refile_non_tray_items = (
            session.query(RefileNonTrayItem)
            .filter(RefileNonTrayItem.non_tray_item_id == non_tray_item.id)
            .all()
        )

        if existing_refile_non_tray_items:
            refile_items_id = [
                refile.refile_job_id for refile in existing_refile_non_tray_items
            ]
            existing_refile_job = (
                session.query(RefileJob)
                .filter(
                    RefileJob.id.in_(refile_items_id),
                    RefileJob.status != "Completed",
                )
                .first()
            )

            if existing_refile_job:
                raise ValidationException(
                    detail=f"Non Tray Item already exists in an "
                    "uncompleted "
                    "refile "
                    f"Job ID: {existing_refile_job.id}"
                )

        existing_pick_list_items = (
            session.query(PickList.id)
            .join(Request, PickList.id == Request.pick_list_id)
            .filter(Request.non_tray_item_id == non_tray_item.id)
            .filter(PickList.status != "Completed")
            .all()
        )

        if existing_pick_list_items:
            raise ValidationException(
                detail=f"Non Tray Item already exists in a uncompleted Pick List Job {existing_pick_list_items}"
            )

        non_tray_item.scanned_for_refile_queue = True
        non_tray_item.scanned_for_refile_queue_dt = update_dt
        non_tray_item.scanned_for_refile = False
        non_tray_item.update_dt = update_dt

        session.add(non_tray_item)

    session.commit()

    if item:
        session.refresh(item)
    if non_tray_item:
        session.refresh(non_tray_item)

    results = {
        "item": item,
        "non_tray_item": non_tray_item,
    }

    return results


@router.delete("/")
def remove_from_refile_queue(
    refile_input: RefileQueueInput, session: Session = Depends(get_session)
):
    """
    Remove an item from the refile queue

    **Args:**
    - id: The ID of the item to remove from the refile queue.

    **Returns:**
    - Refile Queue Detail Output: The refile queue details.

    **Raises:**
    - HTTPException: If the item is not found.
    """
    lookup_barcode_value = refile_input.barcode_value
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_value:
        raise BadRequest(detail="No barcode values found in request")

    barcode = (
        session.query(Barcode).where(Barcode.value == lookup_barcode_value).first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode Value {lookup_barcode_value} not found")

    item = session.query(Item).filter(Item.barcode_id == barcode.id).first()

    if item:
        if not item or not item.scanned_for_refile_queue:
            raise BadRequest(detail=f"Item not found or not in refile queue")

        item.scanned_for_refile_queue = False
        item.scanned_for_refile_queue_dt = None
        item.scanned_for_refile = None
        item.update_dt = update_dt

    else:
        non_tray_item = (
            session.query(NonTrayItem).where(barcode.id == NonTrayItem.barcode_id)
        ).first()

        if not non_tray_item or not non_tray_item.scanned_for_refile_queue:
            raise BadRequest(detail=f"Non Tray Item not found or not in refile queue")

        non_tray_item.scanned_for_refile_queue = False
        non_tray_item.scanned_for_refile_queue_dt = None
        non_tray_item.scanned_for_refile = None
        non_tray_item.update_dt = update_dt

    session.commit()

    raise HTTPException(
        status_code=status.HTTP_200_OK,
        detail=f"Removed barcode: {lookup_barcode_value} item from refile queue",
    )
