# /code/app/routers/refile_queue.py - REFACRORED TO SQLALCHEMY V2

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now
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
from app.models.owners import Owner
from app.models.ils_configurations import ILSConfiguration
from app.ils.factory import get_ils_adapter

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

from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/refile-queue",
    tags=["refile-queue"],
)


@router.get("/", response_model=Page[RefileQueueListOutput], dependencies=[Depends(RequiresPermission("can_access_refile"))])
def get_refile_queue_list(
    params: RefileQueueParams = Depends(),
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a list of refile jobs
    """
    query = get_refile_queue(params)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = RefileQueueSorter(PickList)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.patch("/", response_model=RefileQueueWriteOutput, dependencies=[Depends(RequiresPermission("can_add_refile_item_to_queue"))])
def add_to_refile_queue(
    refile_input: RefileQueueInput, session: Session = Depends(get_session)
):
    """
    Add an item to the refile queue
    """
    lookup_barcode_value = refile_input.barcode_value
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_value:
        raise BadRequest(detail="No barcode value found in request")

    # V2 FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
    barcode = (
        session.execute(select(Barcode).filter(Barcode.value == lookup_barcode_value))
        .scalars()
        .first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode value {lookup_barcode_value} not found")
    if barcode.withdrawn:
        raise ValidationException(detail="Item has already been withdrawn")

    # V2 FIX
    item = session.execute(select(Item).filter(Item.barcode_id == barcode.id)).scalars().first()
    # V2 FIX
    non_tray_item = (
        session.execute(select(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id))
        .scalars()
        .first()
    )

    if item:
        if item.status != "Out":
            raise ValidationException(detail="Item must be in 'Out' status")
        if item.scanned_for_refile_queue:
            raise ValidationException(detail="Item is already in the refile queue")

        # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
        existing_refile_items = (
            session.execute(select(RefileItem).filter(RefileItem.item_id == item.id))
            .scalars()
            .all()
        )

        if existing_refile_items:
            refile_items_id = [refile.refile_job_id for refile in existing_refile_items]
            # V2 FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
            existing_refile_job = (
                session.execute(
                    select(RefileJob)
                    .filter(
                        RefileJob.id.in_(refile_items_id),
                        RefileJob.status != "Completed",
                    )
                )
                .scalars()
                .first()
            )

            if existing_refile_job:
                raise ValidationException(
                    detail=f"Item already exists in an "
                    "uncompleted "
                    "refile "
                    f"Job ID: {existing_refile_job.id}"
                )
        # V2 FIX: session.query().join().filter().all() -> session.execute(select(...)).all() (only need PickList.id)
        existing_pick_list_items = (
            session.execute(
                select(PickList.id)
                .join(Request, PickList.id == Request.pick_list_id)
                .filter(Request.item_id == item.id)
                .filter(PickList.status != "Completed")
            )
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

        # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
        existing_refile_non_tray_items = (
            session.execute(select(RefileNonTrayItem).filter(RefileNonTrayItem.non_tray_item_id == non_tray_item.id))
            .scalars()
            .all()
        )

        if existing_refile_non_tray_items:
            refile_items_id = [
                refile.refile_job_id for refile in existing_refile_non_tray_items
            ]
            # V2 FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
            existing_refile_job = (
                session.execute(
                    select(RefileJob)
                    .filter(
                        RefileJob.id.in_(refile_items_id),
                        RefileJob.status != "Completed",
                    )
                )
                .scalars()
                .first()
            )

            if existing_refile_job:
                raise ValidationException(
                    detail=f"Non Tray Item already exists in an "
                    "uncompleted "
                    "refile "
                    f"Job ID: {existing_refile_job.id}"
                )

        # V2 FIX: session.query().join().filter().all() -> session.execute(select(...)).all() (only need PickList.id)
        existing_pick_list_items = (
            session.execute(
                select(PickList.id)
                .join(Request, PickList.id == Request.pick_list_id)
                .filter(Request.non_tray_item_id == non_tray_item.id)
                .filter(PickList.status != "Completed")
            )
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

        non_tray_item.update_dt = update_dt

    # -- ILS SYNCHRONOUS REFILE INTERCEPT LAYER --
    target_entity = item or non_tray_item
    if target_entity.owner_id:
        owner = session.get(Owner, target_entity.owner_id)
        if owner and owner.resolved_ils_configuration_id:
            config = session.get(ILSConfiguration, owner.resolved_ils_configuration_id)
            if config and config.is_active and config.enable_refile_hook:
                adapter = get_ils_adapter(config)
                
                try:
                    check_in_resp = adapter.check_in_item(lookup_barcode_value)
                    
                    if not check_in_resp.is_valid:
                        raise ValidationException(detail=f"ILS Check-In Failed: {check_in_resp.message or 'Verification failed.'}")
                        
                    if not check_in_resp.status_matches:
                        raise ValidationException(detail=f"ILS Refile Block: Item status is '{check_in_resp.current_status}'. Discharge at Circulation Desk first before returning to facility.")
                        
                except ValidationException:
                    raise
                except HTTPException:
                    raise
                except Exception as e:
                    inventory_logger.error(f"Critical ILS adapter fail on Refile for {lookup_barcode_value}: {e}")
                    raise ValidationException(detail="ILS Synchronization currently unreachable. Cannot verify Refile status.")

    if item:
        session.add(item)
    elif non_tray_item:
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


@router.delete("/", dependencies=[Depends(RequiresPermission("can_add_refile_item_to_queue"))])
def remove_from_refile_queue(
    refile_input: RefileQueueInput, session: Session = Depends(get_session)
):
    """
    Remove an item from the refile queue
    """
    lookup_barcode_value = refile_input.barcode_value
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_value:
        raise BadRequest(detail="No barcode values found in request")

    # V2 FIX: session.query().where().first() -> session.execute(select(...)).scalars().first()
    barcode = (
        session.execute(select(Barcode).where(Barcode.value == lookup_barcode_value))
        .scalars()
        .first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode Value {lookup_barcode_value} not found")

    # V2 FIX
    item = session.execute(select(Item).filter(Item.barcode_id == barcode.id)).scalars().first()

    if item:
        if not item or not item.scanned_for_refile_queue:
            raise BadRequest(detail=f"Item not found or not in refile queue")

        item.scanned_for_refile_queue = False
        item.scanned_for_refile_queue_dt = None
        item.scanned_for_refile = None
        item.update_dt = update_dt

    else:
        # V2 FIX
        non_tray_item = (
            session.execute(select(NonTrayItem).where(Barcode.id == NonTrayItem.barcode_id))
            .scalars()
            .first()
        )

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
