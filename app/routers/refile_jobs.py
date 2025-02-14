from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from sqlalchemy import asc, desc

from app.database.session import get_session, commit_record
from app.filter_params import JobFilterParams, SortParams
from app.models.barcodes import Barcode
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.refile_jobs import RefileJob, RefileJobStatus
from app.models.refile_items import RefileItem
from app.models.refile_non_tray_items import RefileNonTrayItem
from app.models.trays import Tray
from app.schemas.refile_jobs import (
    RefileJobInput,
    RefileJobUpdateInput,
    RefileJobListOutput,
    RefileJobDetailOutput,
)
from app.schemas.items import ItemUpdateInput
from app.schemas.non_tray_items import NonTrayItemUpdateInput
from app.config.exceptions import BadRequest, NotFound
from app.utilities import manage_transition, get_location, get_sorted_query

router = APIRouter(
    prefix="/refile-jobs",
    tags=["refile-jobs"],
)


def sort_order_priority(session, item_type, item):
    if item_type == "item":
        tray = session.get(Tray, item.tray_id)
        location = get_location(session, tray.shelf_position)
    else:
        location = get_location(session, item.shelf_position)

    aisle_priority = (
        location["aisle"].sort_priority or location["aisle"].aisle_number_id
    )

    ladder_priority = (
        location["ladder"].sort_priority or location["ladder"].ladder_number_id
    )

    shelf_priority = (
        location["shelf"].sort_priority or location["shelf"].shelf_number_id
    )

    return {
        item_type: item,
        "aisle_priority": aisle_priority,
        "ladder_priority": ladder_priority,
        "shelf_priority": shelf_priority,
    }


def sorted_requests(session, refile_job):
    request_data = []
    withdrawn_items = []
    withdrawn_non_tray_items = []
    items = refile_job.items
    non_tray_items = refile_job.non_tray_items

    if items:
        for item in items:
            if item.tray:
                if item.tray.shelf_position:
                    request_data.append(sort_order_priority(session, "item", item))
                else:
                    withdrawn_items.append(item)
            else:
                withdrawn_items.append(item)

    if non_tray_items:
        for non_tray_item in non_tray_items:
            if non_tray_item.shelf_position:
                request_data.append(
                    sort_order_priority(session, "non_tray_item", non_tray_item)
                )
            else:
                withdrawn_non_tray_items.append(non_tray_item)

    sort_requests = sorted(
        request_data,
        key=lambda x: (
            x["aisle_priority"],
            x["ladder_priority"],
            x["shelf_priority"],
        ),
    )

    sorted_list = []
    for item in sort_requests:
        if item.get("item"):
            sorted_list.append(item["item"])
        elif item.get("non_tray_item"):
            sorted_list.append(item["non_tray_item"])

    # Append withdrawn items without shelf positions to the end
    sorted_list.extend(withdrawn_items)
    sorted_list.extend(withdrawn_non_tray_items)

    refile_job = refile_job.model_dump()
    refile_job["refile_job_items"] = sorted_list
    refile_job["items"] = items
    refile_job["non_tray_items"] = non_tray_items
    return refile_job


@router.get("/", response_model=Page[RefileJobListOutput])
def get_refile_job_list(
    session: Session = Depends(get_session),
    queue: bool = Query(default=False),
    params: JobFilterParams = Depends(),
    status: RefileJobStatus | None = None,
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a list of refile jobs

    **Parameters:**
    - session: The database session.
    - queue: If true, only return refile jobs that are not completed.
    - params: The filter parameters.
    - status: The status of the refile job.
    - sort_params: The sort parameters.

    **Returns:**
    - Refile Job List Output: The paginated list of refile jobs
    """
    # Create a query to select all Refile Job
    query = select(RefileJob).distinct()

    if queue:
        query = query.where(RefileJob.status != "Completed")
    if params.workflow_id:
        query = query.where(RefileJob.id == params.workflow_id)
    if params.user_id:
        query = query.where(RefileJob.assigned_user_id == params.user_id)
    if params.created_by_id:
        query = query.where(RefileJob.created_by_id == params.created_by_id)
    if params.from_dt:
        query = query.where(RefileJob.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(RefileJob.create_dt <= params.to_dt)
    if status:
        query = query.where(RefileJob.status == status.value)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(RefileJob, query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=RefileJobDetailOutput)
def get_refile_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve refile job details by ID.

    **Args:**
    - id: The ID of the refile job to retrieve.

    **Returns:**
    - Refile Job Detail Output: The refile job details.

    **Raises:**
    - Not Found HTTPException: If the refile job is not found.
    """
    refile_job = session.get(RefileJob, id)

    if refile_job:
        if not refile_job.items and not refile_job.non_tray_items:
            return refile_job
        refile_job = sorted_requests(session, refile_job)
        return refile_job
    else:
        raise NotFound(detail=f"Refile Job ID {id} Not Found")


@router.post("/", response_model=RefileJobDetailOutput, status_code=201)
def create_refile_job(
    refile_job_input: RefileJobInput, session: Session = Depends(get_session)
):
    """
    Create a new refile job.

    **Args:**
    - Refile Job Input: The refile job data to create.

    **Returns:**
    - Refile Job Detail Output: The created refile job details.

    **Raises:**
    - Validation HTTPException: If the refile job already exists.
    """

    lookup_barcode_values = refile_job_input.barcode_values
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_values:
        raise BadRequest(detail="At least one barcode value must be provided")

    new_refile_job = commit_record(session, RefileJob(**refile_job_input.model_dump()))
    session.flush()

    refile_items = []
    refile_non_tray_items = []
    errored_barcodes = []

    barcodes = (
        session.query(Barcode).filter(Barcode.value.in_(lookup_barcode_values)).all()
    )
    items_map = {
        barcode.id: session.query(Item).filter(Item.barcode_id == barcode.id).first()
        for barcode in barcodes
    }
    non_tray_items_map = {
        barcode.id: session.query(NonTrayItem)
        .filter(NonTrayItem.barcode_id == barcode.id)
        .first()
        for barcode in barcodes
    }

    for barcode in barcodes:
        item = items_map.get(barcode.id)
        non_tray_item = non_tray_items_map.get(barcode.id)

        if item:
            existing_refile_items = (
                session.query(RefileItem).filter(RefileItem.item_id == item.id).all()
            )
            if existing_refile_items:
                refile_job_ids = [
                    refile.refile_job_id for refile in existing_refile_items
                ]
                requests = (
                    session.query(RefileJob)
                    .filter(
                        RefileJob.id.in_(refile_job_ids),
                        RefileJob.status != "Completed",
                    )
                    .all()
                )
                if requests:
                    errored_barcodes.append(barcode.value)
                    continue

            refile_items.append(
                RefileItem(refile_job_id=new_refile_job.id, item_id=item.id)
            )
            item.scanned_for_refile_queue = False
            item.scanned_for_refile_queue_dt = None
            item.update_dt = update_dt
            session.add(item)

        elif non_tray_item:
            existing_refile_non_tray_items = (
                session.query(RefileNonTrayItem)
                .filter(RefileNonTrayItem.non_tray_item_id == non_tray_item.id)
                .all()
            )

            if existing_refile_non_tray_items:
                refile_job_ids = [
                    refile.refile_job_id for refile in existing_refile_non_tray_items
                ]
                requests = (
                    session.query(RefileJob)
                    .filter(
                        RefileJob.id.in_(refile_job_ids),
                        RefileJob.status != "Completed",
                    )
                    .all()
                )

                if requests:
                    errored_barcodes.append(barcode.value)
                    continue

            refile_non_tray_items.append(
                RefileNonTrayItem(
                    refile_job_id=new_refile_job.id, non_tray_item_id=non_tray_item.id
                )
            )

            non_tray_item.scanned_for_refile_queue = False
            non_tray_item.scanned_for_refile_queue_dt = None
            non_tray_item.update_dt = update_dt
            session.add(non_tray_item)

        else:
            errored_barcodes.append(barcode.value)

    if refile_items:
        session.bulk_save_objects(refile_items)
    if refile_non_tray_items:
        session.bulk_save_objects(refile_non_tray_items)

    session.commit()
    session.refresh(new_refile_job)

    if not new_refile_job.items and not new_refile_job.non_tray_items:
        return new_refile_job
    return sorted_requests(session, new_refile_job)


@router.patch("/{id}", response_model=RefileJobDetailOutput)
def update_refile_job(
    id: int, refile_job: RefileJobUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an existing refile job.

    **Args:**
    - id: The ID of the refile job to update.
    - refile_job: The updated refile job data.

    **Returns:**
    - Refile Job Detail Output: The updated refile job details.

    **Raises:**
    - Not Found HTTPException: If the refile job is not found.
    """
    existing_refile_job = session.get(RefileJob, id)

    if not existing_refile_job:
        raise NotFound(detail=f"Refile Job ID {id} Not Found")

    if refile_job.status and refile_job.run_timestamp:
        existing_refile_job = manage_transition(existing_refile_job, refile_job)

    mutated_data = refile_job.model_dump(exclude_unset=True, exclude={"run_timestamp"})

    for key, value in mutated_data.items():
        setattr(existing_refile_job, key, value)

    setattr(existing_refile_job, "update_dt", datetime.now(timezone.utc))

    session.add(existing_refile_job)
    session.commit()
    session.refresh(existing_refile_job)

    if not existing_refile_job.items and not existing_refile_job.non_tray_items:
        return existing_refile_job
    return sorted_requests(session, existing_refile_job)


@router.delete("/{id}")
def delete_refile_job(id: int, session: Session = Depends(get_session)):
    """
    Delete a refile job by ID.

    **Args:**
    - id: The ID of the refile job to delete.

    **Returns:**
    - None

    **Raises:**
    - Not Found HTTPException: If the refile job is not found.
    """
    refile_job = session.query(RefileJob).filter(RefileJob.id == id).first()

    if not refile_job:
        raise NotFound(detail=f"Refile Job ID {id} Not Found")

    refile_items = (
        session.query(RefileItem).filter(RefileItem.refile_job_id == id).all()
    )
    refile_non_tray_items = (
        session.query(RefileNonTrayItem)
        .filter(RefileNonTrayItem.refile_job_id == id)
        .all()
    )

    item_ids = [refile_item.item_id for refile_item in refile_items]
    non_tray_item_ids = [
        refile_non_tray_item.non_tray_item_id
        for refile_non_tray_item in refile_non_tray_items
    ]

    update_dt = datetime.now(timezone.utc)

    session.query(Item).filter(Item.id.in_(item_ids)).update(
        {
            "scanned_for_refile_queue": True,
            "scanned_for_refile_queue_dt": update_dt,
            "update_dt": update_dt,
        },
        synchronize_session="fetch",
    )

    session.query(NonTrayItem).filter(NonTrayItem.id.in_(non_tray_item_ids)).update(
        {
            "scanned_for_refile_queue": True,
            "scanned_for_refile_queue_dt": update_dt,
            "update_dt": update_dt,
        },
        synchronize_session="fetch",
    )

    # Delete refile items
    session.query(RefileItem).filter(RefileItem.refile_job_id == id).delete(
        synchronize_session=False
    )
    # Delete non-tray items
    session.query(RefileNonTrayItem).filter(
        RefileNonTrayItem.refile_job_id == id
    ).delete(synchronize_session=False)
    # Delete refile job
    session.delete(refile_job)
    session.commit()

    return HTTPException(
        status_code=204, detail=f"Refile Job ID {id} Deleted Successfully"
    )


@router.post("/{job_id}/add_items", response_model=RefileJobDetailOutput)
def add_items_to_refile_job(
    job_id: int,
    refile_job_input: RefileJobInput,
    session: Session = Depends(get_session),
):
    """
    Add an item to a refile job.

    **Args:**
    - job_id: The ID of the refile job to add the item to.
    - Refile Job Input: The list of barcode values of the items and non tray items to add to
    the refile job.

    **Returns:**
    - Refile Job Detail Output: The updated refile job details.

    **Raises:**
    - Not Found HTTPException: If the refile job or item is not found.
    """
    lookup_barcode_values = refile_job_input.barcode_values
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_values:
        raise BadRequest(detail="At least one barcode value must be provided")

    refile_job = session.get(RefileJob, job_id)

    if not refile_job:
        raise NotFound(detail=f"Refile Job ID {job_id} Not Found")

    refile_items = []
    refile_non_tray_items = []
    errored_barcodes = []

    barcodes = (
        session.query(Barcode).filter(Barcode.value.in_(lookup_barcode_values)).all()
    )
    items_map = {
        barcode.id: session.query(Item).filter(Item.barcode_id == barcode.id).first()
        for barcode in barcodes
    }
    non_tray_items_map = {
        barcode.id: session.query(NonTrayItem)
        .filter(NonTrayItem.barcode_id == barcode.id)
        .first()
        for barcode in barcodes
    }

    for barcode in barcodes:
        item = items_map.get(barcode.id)
        non_tray_item = non_tray_items_map.get(barcode.id)

        if item:
            existing_refile_items = (
                session.query(RefileItem).filter(RefileItem.item_id == item.id).all()
            )

            if existing_refile_items:
                refile_job_ids = [
                    refile.refile_job_id for refile in existing_refile_items
                ]
                requests = (
                    session.query(RefileJob)
                    .filter(
                        RefileJob.id.in_(refile_job_ids),
                        RefileJob.status != "Completed",
                    )
                    .all()
                )

                if requests:
                    errored_barcodes.append(barcode.value)
                    continue

            refile_items.append(
                RefileItem(refile_job_id=refile_job.id, item_id=item.id)
            )

            item.scanned_for_refile_queue = False
            item.scanned_for_refile_queue_dt = None
            item.update_dt = update_dt

        elif non_tray_item:
            existing_refile_non_tray_items = (
                session.query(RefileNonTrayItem)
                .filter(RefileNonTrayItem.non_tray_item_id == non_tray_item.id)
                .all()
            )

            if existing_refile_non_tray_items:
                refile_job_ids = [
                    refile.refile_job_id for refile in existing_refile_non_tray_items
                ]
                requests = (
                    session.query(RefileJob)
                    .filter(
                        RefileJob.id.in_(refile_job_ids),
                        RefileJob.status != "Completed",
                    )
                    .all()
                )

                if requests:
                    errored_barcodes.append(barcode.value)
                    continue

            refile_non_tray_items.append(
                RefileNonTrayItem(
                    refile_job_id=refile_job.id, non_tray_item_id=non_tray_item.id
                )
            )

            non_tray_item.scanned_for_refile_queue = False
            non_tray_item.scanned_for_refile_queue_dt = None
            non_tray_item.update_dt = update_dt

    session.bulk_save_objects(refile_items)
    session.bulk_save_objects(refile_non_tray_items)
    session.commit()
    session.refresh(refile_job)

    if not refile_job.items and not refile_job.non_tray_items:
        return refile_job
    return sorted_requests(session, refile_job)


@router.delete("/{job_id}/remove_items", response_model=RefileJobDetailOutput)
def remove_item_from_refile_job(
    job_id: int,
    refile_job_input: RefileJobInput,
    session: Session = Depends(get_session),
):
    """
    Remove an item from a refile job.

    **Args:**
    - job_id: The ID of the refile job to remove the item from.
    - Refile Job Input: The list of barcode values of items and non tray items to remove
    from the refile job.

    **Returns:**
    - Refile Job Detail Output: The updated refile job details.

    **Raises:**
    - Not Found HTTPException: If the refile job or item is not found.
    """

    lookup_barcode_values = refile_job_input.barcode_values
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_values:
        raise BadRequest(detail="At least one barcode value must be provided")

    refile_job = session.get(RefileJob, job_id)

    if not refile_job:
        raise NotFound(detail=f"Refile Job ID {job_id} Not Found")

    barcodes = (
        session.query(Barcode).filter(Barcode.value.in_(lookup_barcode_values)).all()
    )
    items_map = {
        barcode.id: session.query(Item).filter(Item.barcode_id == barcode.id).first()
        for barcode in barcodes
    }
    non_tray_items_map = {
        barcode.id: session.query(NonTrayItem)
        .filter(NonTrayItem.barcode_id == barcode.id)
        .first()
        for barcode in barcodes
    }

    for barcode in barcodes:
        item = items_map.get(barcode.id)
        non_tray_item = non_tray_items_map.get(barcode.id)

        if item:
            refile_item = (
                session.query(RefileItem)
                .filter(
                    RefileItem.refile_job_id == job_id, RefileItem.item_id == item.id
                )
                .first()
            )

            if refile_item:
                session.delete(refile_item)
                item.scanned_for_refile_queue = True
                item.update_dt = update_dt
        elif non_tray_item:
            non_tray_item = (
                session.query(NonTrayItem)
                .filter(NonTrayItem.barcode_id == barcode.id)
                .first()
            )

            refile_non_tray_item = (
                session.query(RefileNonTrayItem)
                .filter(
                    RefileNonTrayItem.refile_job_id == job_id,
                    RefileNonTrayItem.non_tray_item_id == non_tray_item.id,
                )
                .first()
            )

            if refile_non_tray_item:
                session.delete(refile_non_tray_item)
                non_tray_item.scanned_for_refile_queue = True
                non_tray_item.update_dt = update_dt

    session.commit()
    session.refresh(refile_job)

    if not refile_job.items and not refile_job.non_tray_items:
        return refile_job
    return sorted_requests(session, refile_job)


@router.patch("/{job_id}/update_item/{item_id}", response_model=RefileJobDetailOutput)
def update_item_in_refile_job(
    job_id: int,
    item_id: int,
    refile_job_item_input: ItemUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update an item in a refile job.

    **Args:**
    - job_id: The ID of the refile job to update the item in.
    - item_id: The ID of the item to update.
    - Refile Job Input: The list of barcode values of items and non tray items to update
    in the refile job.

    **Returns:**
    - Refile Job Detail Output: The updated refile job details.

    **Raises:**
    - Not Found HTTPException: If the refile job or item is not found.
    """

    refile_job = session.get(RefileJob, job_id)

    if not refile_job:
        raise NotFound(detail=f"Refile Job ID {job_id} not found")

    existing_item = session.query(Item).filter(Item.id == item_id).first()

    if not existing_item:
        raise NotFound(detail=f"Item ID {item_id} not found")

    # Update the item record with the mutated data
    mutated_data = refile_job_item_input.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_item, key, value)
    setattr(existing_item, "update_dt", datetime.now(timezone.utc))

    # Commit the changes to the database
    session.add(existing_item)
    session.commit()

    session.refresh(refile_job)

    if not refile_job.items and not refile_job.non_tray_items:
        return refile_job
    return sorted_requests(session, refile_job)


@router.patch(
    "/{job_id}/update_non_tray_items/{non_tray_item_id}",
    response_model=RefileJobDetailOutput,
)
def update_non_tray_item_in_refile_job(
    job_id: int,
    non_tray_item_id: int,
    refile_job_non_tray_item_input: NonTrayItemUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a Non Tray item in a refile job.

    **Args:**
    - job_id: The ID of the refile job to update the item in.
    - non_tray_item_id: The ID of the non tray item to update.
    - Refile Job Input: The list of barcode values of items and non tray items to update
    in the refile job.

    **Returns:**
    - Refile Job Detail Output: The updated refile job details.

    **Raises:**
    - Not Found HTTPException: If the refile job or non tray item is not found.
    """

    refile_job = session.get(RefileJob, job_id)

    if not refile_job:
        raise NotFound(detail=f"Refile Job ID {job_id} not found")

    existing_item = (
        session.query(NonTrayItem).filter(NonTrayItem.id == non_tray_item_id).first()
    )

    if not existing_item:
        raise NotFound(detail=f"Non Tray Item ID {non_tray_item_id} not found")

    # Update the item record with the mutated data
    mutated_data = refile_job_non_tray_item_input.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_item, key, value)
    setattr(existing_item, "update_dt", datetime.now(timezone.utc))

    # Commit the changes to the database
    session.add(existing_item)
    session.commit()

    session.refresh(refile_job)

    if not refile_job.items and not refile_job.non_tray_items:
        return refile_job
    return sorted_requests(session, refile_job)
