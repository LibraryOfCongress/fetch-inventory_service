from datetime import datetime
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
from app.models.refile_items import RefileItem
from app.models.refile_jobs import RefileJob
from app.models.refile_non_tray_item import RefileNonTrayItem

from app.schemas.refile_queue import (
    RefileQueueInput,
    RefileQueueListOutput,
    RefileQueueWriteOutput,
    TrayNestedForRefileQueue,
    NonTrayNestedForRefileQueue,
)
from app.config.exceptions import BadRequest
from app.utilities import get_refile_queue


router = APIRouter(
    prefix="/refile-queue",
    tags=["refile-queue"],
)


@router.get("/", response_model=Page[RefileQueueListOutput])
def get_refile_queue_list(
    building_id: int = None,
    session: Session = Depends(get_session),
) -> list:
    """
    Get a list of refile jobs

    **Args:**
    - scanned_queue: Whether to get the scanned queue or not
    - building_id: The ID of the building

    **Returns:**
    - Refile Job List Output: The paginated list of refile jobs
    """
    return paginate(session, get_refile_queue(building_id))


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
    lookup_barcode_values = refile_input.barcode_values
    update_dt = datetime.utcnow()

    if not lookup_barcode_values:
        raise BadRequest(detail="No barcode values found in request")

    barcodes = (
        session.query(Barcode).filter(Barcode.value.in_(lookup_barcode_values)).all()
    )
    barcode_ids = {barcode.value: barcode.id for barcode in barcodes}

    items = session.query(Item).filter(Item.barcode_id.in_(barcode_ids.values())).all()
    non_tray_items = (
        session.query(NonTrayItem)
        .filter(NonTrayItem.barcode_id.in_(barcode_ids.values()))
        .all()
    )

    successful_items = []
    successful_non_tray_items = []
    errored_barcodes = []

    for barcode_value in lookup_barcode_values:
        barcode_id = barcode_ids.get(barcode_value)
        if not barcode_id:
            errored_barcodes.append(barcode_value)
            continue

        item = next((item for item in items if item.barcode_id == barcode_id), None)
        non_tray_item = next(
            (nt_item for nt_item in non_tray_items if nt_item.barcode_id == barcode_id),
            None,
        )

        if item:
            existing_refile_items = (
                session.query(RefileItem).filter(RefileItem.item_id == item.id).all()
            )

            if existing_refile_items:
                refile_items_id = [
                    refile.refile_job_id for refile in existing_refile_items
                ]
                existing_refile_job = (
                    session.query(RefileJob)
                    .filter(
                        RefileJob.id.in_(refile_items_id),
                        RefileJob.status != "Completed",
                    )
                    .all()
                )

                if existing_refile_job:
                    errored_barcodes.append(barcode_value)
                    continue

            if item.scanned_for_refile_queue or item.status == "In":
                errored_barcodes.append(barcode_value)
                continue

            item.scanned_for_refile_queue = True
            item.scanned_for_refile_queue_dt = update_dt
            item.update_dt = update_dt
            successful_items.append(item)

        elif non_tray_item:
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
                    .all()
                )

                if existing_refile_job:
                    errored_barcodes.append(barcode_value)
                    continue

            if non_tray_item.scanned_for_refile_queue or non_tray_item.status == "In":
                errored_barcodes.append(barcode_value)
                continue

            non_tray_item.scanned_for_refile_queue = True
            non_tray_item.scanned_for_refile_queue_dt = update_dt
            non_tray_item.update_dt = update_dt
            successful_non_tray_items.append(non_tray_item)

    session.commit()

    added_successfully = list(set(lookup_barcode_values) - set(errored_barcodes))

    if not added_successfully:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add Barcodes: {lookup_barcode_values} from refile "
            f"queue",
        )

    results = {
        "errored_barcodes": errored_barcodes,
        "items": successful_items,
        "non_tray_items": successful_non_tray_items,
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
    lookup_barcode_values = refile_input.barcode_values
    errored_barcodes = []
    update_dt = datetime.utcnow()

    if not lookup_barcode_values:
        raise BadRequest(detail="No barcode values found in request")

    for barcode_value in lookup_barcode_values:
        barcode = session.query(Barcode).where(Barcode.value == barcode_value).first()

        if not barcode:
            errored_barcodes.append(barcode_value)
            continue

        item = session.query(Item).filter(Item.barcode_id == barcode.id).first()

        if item:
            if not item.scanned_for_refile_queue:
                errored_barcodes.append(barcode_value)
                continue

            item.scanned_for_refile_queue = False
            item.scanned_for_refile_queue_dt = None
            item.update_dt = update_dt

        else:
            non_tray_item = (
                session.query(NonTrayItem).where(barcode.id == NonTrayItem.barcode_id)
            ).first()

            if not non_tray_item or not non_tray_item.scanned_for_refile_queue:
                errored_barcodes.append(barcode_value)
                continue

            non_tray_item.scanned_for_refile_queue = False
            non_tray_item.scanned_for_refile_queue_dt = None
            non_tray_item.update_dt = update_dt

    session.commit()

    if errored_barcodes:
        added_successfully = list(set(lookup_barcode_values) - set(errored_barcodes))

        if not added_successfully:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to removed barcodes: {lookup_barcode_values} from "
                f"refile "
                f"queue",
            )

        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail=f"Removed barcodes: {added_successfully} and failed to remove "
            f"barcodes:"
            f" {errored_barcodes} to refile queue",
        )

    raise HTTPException(
        status_code=status.HTTP_200_OK,
        detail=f"Removed barcodes: {lookup_barcode_values} items from refile queue",
    )
