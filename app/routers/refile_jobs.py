# /code/app/routers/refile_jobs.py - FINAL FIX (BARCODE_VALUES EXCLUSION + V2 SYNTAX)

from datetime import datetime, timezone

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session 
from sqlalchemy import select, func, update, and_, delete 
from sqlalchemy.exc import IntegrityError
from typing import Optional, List

from app.database.session import get_session, commit_record
from app.filter_params import SortParams, JobFilterParams
from app.models.barcodes import Barcode
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.refile_jobs import RefileJob
from app.models.refile_items import RefileItem
from app.models.refile_non_tray_items import RefileNonTrayItem
from app.models.trays import Tray
from app.models.users import User
from app.schemas.refile_jobs import (
    RefileJobInput,
    RefileJobUpdateInput,
    RefileJobListOutput,
    RefileJobDetailOutput,
)
from app.schemas.items import ItemUpdateInput
from app.schemas.non_tray_items import NonTrayItemUpdateInput
from app.config.exceptions import BadRequest, NotFound
from app.sorting import RefileJobSorter
from app.utilities import manage_transition, get_location

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.utils.job_assignment import auto_assign_on_start, update_status_on_assignment, validate_assignment_lock
from app.services.audit_service import log_audit_event, AuditEventType

router = APIRouter(
    prefix="/refile-jobs",
    tags=["refile-jobs"],
)


def sort_order_priority(session: Session, item_type, item):
    if item_type == "item":
        tray = session.get(Tray, item.tray_id)
        location = get_location(session, tray.shelf_position)
    else:
        location = get_location(session, item.shelf_position)

    aisle_priority = location["aisle"].sort_priority or location["aisle"].aisle_number

    ladder_priority = (
        location["ladder"].sort_priority or location["ladder"].ladder_number
    )

    shelf_priority = location["shelf"].sort_priority or location["shelf"].shelf_number

    return {
        item_type: item,
        "aisle_priority": aisle_priority,
        "ladder_priority": ladder_priority,
        "shelf_priority": shelf_priority,
    }


def sorted_requests(session: Session, refile_job):
    request_data = []
    withdrawn_items = []
    withdrawn_non_tray_items = []
    assigned_user = None
    created_by = None

    items = refile_job.items
    non_tray_items = refile_job.non_tray_items

    if refile_job.assigned_user:
        assigned_user = refile_job.assigned_user
    if refile_job.created_by:
        created_by = refile_job.created_by
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

    # Final sort of already location-prioritized items by update_dt
    unfulfilled_requests = [list_item for list_item in sorted_list if not list_item.scanned_for_refile]
    fulfilled_requests = [list_item for list_item in sorted_list if list_item.scanned_for_refile]
    # Append withdrawn items without shelf positions to the end
    sorted_list = unfulfilled_requests + fulfilled_requests
    sorted_list.extend(withdrawn_items)
    sorted_list.extend(withdrawn_non_tray_items)

    refile_job = refile_job.__dict__.copy() # Use copy to allow adding keys
    refile_job["refile_job_items"] = sorted_list
    refile_job["items"] = items
    refile_job["non_tray_items"] = non_tray_items
    refile_job["assigned_user"] = assigned_user
    refile_job["created_by"] = created_by
    return refile_job


@router.get("/", response_model=Page[RefileJobListOutput], dependencies=[Depends(RequiresPermission("can_access_refile"))])
def get_refile_job_list(
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get a list of refile jobs
    """
    # Create a query to select all Refile Job
    query = select(RefileJob)

    if params.queue:
        query = query.where(RefileJob.status != "Completed")
    if params.status and len(list(filter(None, params.status))) > 0:
        query = query.where(RefileJob.status.in_(params.status))
    if params.workflow_id:
        query = query.where(RefileJob.id == params.workflow_id)
    if params.assigned_user_id:
        query = query.where(RefileJob.assigned_user_id.in_(params.assigned_user_id))
    if params.assigned_user:
        assigned_user_subquery = select(User.id).where(
            func.concat(User.first_name, " ", User.last_name).in_(params.assigned_user)
        ).scalar_subquery()
        query = query.where(RefileJob.assigned_user_id.in_(assigned_user_subquery))
    if params.created_by_id:
        query = query.where(RefileJob.created_by_id == params.created_by_id)
    if params.from_dt:
        query = query.where(RefileJob.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(RefileJob.create_dt <= params.to_dt)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using RequestSorter
        sorter = RefileJobSorter(RefileJob)
        query = sorter.apply_sorting(query, sort_params)

    # CRITICAL FIX: Paginate now takes only the query object
    return paginate(session, query)


@router.get("/{id}", response_model=RefileJobDetailOutput, dependencies=[Depends(RequiresPermission("can_access_refile"))])
def get_refile_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve refile job details by ID.
    """
    refile_job = session.get(RefileJob, id)

    if refile_job:
        if not refile_job.items and not refile_job.non_tray_items:
            return refile_job
        refile_job = sorted_requests(session, refile_job)
        return refile_job
    else:
        raise NotFound(detail=f"Refile Job ID {id} Not Found")


@router.post("/", response_model=RefileJobDetailOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_create_refile_job"))])
def create_refile_job(
    refile_job_input: RefileJobInput, session: Session = Depends(get_session)
):
    """
    Create a new refile job.
    """

    lookup_barcode_values = refile_job_input.barcode_values
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_values:
        raise BadRequest(detail="At least one barcode value must be provided")

    # CRITICAL FIX: Exclude 'barcode_values' from the constructor
    refile_job_data = refile_job_input.model_dump(exclude={"barcode_values"})
    new_refile_job = commit_record(session, RefileJob(**refile_job_data))
    session.flush()

    refile_items = []
    refile_non_tray_items = []
    errored_barcodes = []

    # V2 FIX
    barcodes = (
        session.execute(select(Barcode).filter(Barcode.value.in_(lookup_barcode_values)))
        .scalars()
        .all()
    )
    
    # V2 FIX: Optimize loop lookups
    items_map = {}
    non_tray_items_map = {}
    
    for barcode in barcodes:
        # Check Item
        item = session.execute(select(Item).filter(Item.barcode_id == barcode.id)).scalars().first()
        if item:
            items_map[barcode.id] = item
        else:
            # Check NonTrayItem
            non_tray_item = session.execute(select(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id)).scalars().first()
            if non_tray_item:
                non_tray_items_map[barcode.id] = non_tray_item

    for barcode in barcodes:
        item = items_map.get(barcode.id)
        non_tray_item = non_tray_items_map.get(barcode.id)

        if item:
            # V2 FIX
            existing_refile_items = (
                session.execute(select(RefileItem).filter(RefileItem.item_id == item.id))
                .scalars()
                .all()
            )
            if existing_refile_items:
                refile_job_ids = [
                    refile.refile_job_id for refile in existing_refile_items
                ]
                # V2 FIX
                requests = (
                    session.execute(select(RefileJob)
                        .filter(
                            RefileJob.id.in_(refile_job_ids),
                            RefileJob.status != "Completed",
                        )
                    )
                    .scalars()
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
            # V2 FIX
            existing_refile_non_tray_items = (
                session.execute(select(RefileNonTrayItem).filter(RefileNonTrayItem.non_tray_item_id == non_tray_item.id))
                .scalars()
                .all()
            )

            if existing_refile_non_tray_items:
                refile_job_ids = [
                    refile.refile_job_id for refile in existing_refile_non_tray_items
                ]
                # V2 FIX
                requests = (
                    session.execute(select(RefileJob)
                        .filter(
                            RefileJob.id.in_(refile_job_ids),
                            RefileJob.status != "Completed",
                        )
                    )
                    .scalars()
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

    log_audit_event(
        session,
        AuditEventType.JOB_CREATED,
        f"Refile Job {new_refile_job.id} created with {len(refile_items) + len(refile_non_tray_items)} items",
        job_type="refile_jobs",
        job_id=new_refile_job.id,
    )
    session.commit()

    if not new_refile_job.items and not new_refile_job.non_tray_items:
        return new_refile_job
    return sorted_requests(session, new_refile_job)


@router.patch("/{id}", response_model=RefileJobDetailOutput, dependencies=[Depends(RequiresPermission("process_refile_jobs"))])
def update_refile_job(
    id: int, 
    refile_job: RefileJobUpdateInput, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Update an existing refile job.
    
    Includes auto-assignment logic:
    - When a user starts a job (status → Running), auto-assign to them if unassigned
    - Prevent users from starting jobs assigned to others
    - When manager assigns a user, auto-update status to Assigned
    """
    existing_refile_job = session.get(RefileJob, id)

    if not existing_refile_job:
        raise NotFound(detail=f"Refile Job ID {id} Not Found")
    
    # Capture original status before changes
    original_status = existing_refile_job.status
    original_assigned_user_id = existing_refile_job.assigned_user_id

    # Handle auto-assignment when user starts job
    if refile_job.status:
        auto_assign_on_start(
            existing_refile_job, 
            refile_job.status, 
            current_user.id
        )
    
    # Handle status update when manager assigns user
    if refile_job.assigned_user_id is not None and not refile_job.status:
        update_status_on_assignment(
            existing_refile_job,
            refile_job.assigned_user_id,
            original_status
        )

    if refile_job.status and refile_job.run_timestamp:
        existing_refile_job = manage_transition(existing_refile_job, refile_job)

    mutated_data = refile_job.model_dump(exclude_unset=True, exclude={"run_timestamp"})

    for key, value in mutated_data.items():
        setattr(existing_refile_job, key, value)

    setattr(existing_refile_job, "update_dt", datetime.now(timezone.utc))

    session.add(existing_refile_job)
    session.commit()
    session.refresh(existing_refile_job)

    # Log status change if status was updated
    new_status_val = mutated_data.get("status")
    if new_status_val and new_status_val != original_status:
        log_audit_event(
            session,
            AuditEventType.JOB_STATUS_CHANGED,
            f"Status changed from {original_status} to {new_status_val}",
            job_type="refile_jobs",
            job_id=id,
        )
        session.commit()
    
    target_assigned_user = (
        refile_job.assigned_user_id
        if refile_job.assigned_user_id is not None
        else getattr(existing_refile_job, "assigned_user_id", None)
    )

    if original_assigned_user_id != target_assigned_user:
        user_msg = "Reassigned" if original_assigned_user_id else "Assigned"
        if target_assigned_user:
            assigned_to_user = session.get(User, target_assigned_user)
            assigned_name = assigned_to_user.first_name + " " + assigned_to_user.last_name if assigned_to_user else str(target_assigned_user)
            log_audit_event(
                session,
                AuditEventType.JOB_ASSIGNED,
                f"Refile Job {id} {user_msg.lower()} to {assigned_name}",
                job_type="refile_jobs",
                job_id=id,
            )
        else:
            log_audit_event(
                session,
                AuditEventType.JOB_ASSIGNED,
                f"Refile Job {id} unassigned",
                job_type="refile_jobs",
                job_id=id,
            )
        session.commit()

    if not existing_refile_job.items and not existing_refile_job.non_tray_items:
        return existing_refile_job
    return sorted_requests(session, existing_refile_job)


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_delete_refile_job"))])
def delete_refile_job(id: int, session: Session = Depends(get_session)):
    """
    Delete a refile job by ID.
    """
    # V2 FIX
    refile_job = session.execute(select(RefileJob).filter(RefileJob.id == id)).scalars().first()

    if not refile_job:
        raise NotFound(detail=f"Refile Job ID {id} Not Found")

    # V2 FIX
    refile_items = (
        session.execute(select(RefileItem).filter(RefileItem.refile_job_id == id))
        .scalars()
        .all()
    )
    # V2 FIX
    refile_non_tray_items = (
        session.execute(select(RefileNonTrayItem).filter(RefileNonTrayItem.refile_job_id == id))
        .scalars()
        .all()
    )

    item_ids = [refile_item.item_id for refile_item in refile_items]
    non_tray_item_ids = [
        refile_non_tray_item.non_tray_item_id
        for refile_non_tray_item in refile_non_tray_items
    ]

    update_dt = datetime.now(timezone.utc)

    # V2 UPDATE FIX
    if item_ids:
        session.execute(
            update(Item).where(Item.id.in_(item_ids)).values(
                scanned_for_refile_queue=True,
                scanned_for_refile_queue_dt=update_dt,
                scanned_for_refile=False,
                scanned_for_refile_dt=None,
                update_dt=update_dt,
            )
        )

    # V2 UPDATE FIX
    if non_tray_item_ids:
        session.execute(
            update(NonTrayItem).where(NonTrayItem.id.in_(non_tray_item_ids)).values(
                scanned_for_refile_queue=True,
                scanned_for_refile_queue_dt=update_dt,
                scanned_for_refile=False,
                scanned_for_refile_dt=None,
                update_dt=update_dt,
            )
        )

    # V2 DELETE FIX
    session.execute(
        delete(RefileItem).where(RefileItem.refile_job_id == id)
    )
    # V2 DELETE FIX
    session.execute(
        delete(RefileNonTrayItem).where(RefileNonTrayItem.refile_job_id == id)
    )
    # Delete refile job
    log_audit_event(
        session,
        AuditEventType.JOB_DELETED,
        f"Refile Job {id} deleted",
        job_type="refile_jobs",
        job_id=id,
    )
    session.delete(refile_job)
    session.commit()

    return Response(status_code=204)


@router.post("/{job_id}/add_items", response_model=RefileJobDetailOutput, dependencies=[Depends(RequiresPermission("process_refile_jobs"))])
def add_items_to_refile_job(
    job_id: int,
    refile_job_input: RefileJobInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Add an item to a refile job.
    """
    lookup_barcode_values = refile_job_input.barcode_values
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_values:
        raise BadRequest(detail="At least one barcode value must be provided")

    refile_job = session.get(RefileJob, job_id)

    if not refile_job:
        raise NotFound(detail=f"Refile Job ID {job_id} Not Found")
        
    validate_assignment_lock(refile_job, current_user.id)

    if refile_job.status in ["Running", "Completed"]:
        raise BadRequest(
            detail=f"""Can not add to Refile Job ID {job_id} in '{refile_job.status}' status"""
        )

    refile_items = []
    refile_non_tray_items = []
    errored_barcodes = []

    # V2 FIX
    barcodes = (
        session.execute(select(Barcode).filter(Barcode.value.in_(lookup_barcode_values)))
        .scalars()
        .all()
    )
    
    items_map = {}
    non_tray_items_map = {}

    for barcode in barcodes:
        item = session.execute(select(Item).filter(Item.barcode_id == barcode.id)).scalars().first()
        if item:
            items_map[barcode.id] = item
        else:
            nt = session.execute(select(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id)).scalars().first()
            if nt:
                non_tray_items_map[barcode.id] = nt

    for barcode in barcodes:
        item = items_map.get(barcode.id)
        non_tray_item = non_tray_items_map.get(barcode.id)

        if item:
            # V2 FIX
            existing_refile_items = (
                session.execute(select(RefileItem).filter(RefileItem.item_id == item.id))
                .scalars()
                .all()
            )

            if existing_refile_items:
                refile_job_ids = [
                    refile.refile_job_id for refile in existing_refile_items
                ]
                # V2 FIX
                requests = (
                    session.execute(select(RefileJob)
                        .filter(
                            RefileJob.id.in_(refile_job_ids),
                            RefileJob.status != "Completed",
                        )
                    )
                    .scalars()
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
            item.scanned_for_refile = False
            item.scanned_for_refile_dt = None
            item.update_dt = update_dt

        elif non_tray_item:
            # V2 FIX
            existing_refile_non_tray_items = (
                session.execute(select(RefileNonTrayItem).filter(RefileNonTrayItem.non_tray_item_id == non_tray_item.id))
                .scalars()
                .all()
            )

            if existing_refile_non_tray_items:
                refile_job_ids = [
                    refile.refile_job_id for refile in existing_refile_non_tray_items
                ]
                # V2 FIX
                requests = (
                    session.execute(select(RefileJob)
                        .filter(
                            RefileJob.id.in_(refile_job_ids),
                            RefileJob.status != "Completed",
                        )
                    )
                    .scalars()
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
            non_tray_item.scanned_for_refile = False
            non_tray_item.scanned_for_refile_dt = None
            non_tray_item.update_dt = update_dt

    session.bulk_save_objects(refile_items)
    session.bulk_save_objects(refile_non_tray_items)
    session.commit()
    session.refresh(refile_job)

    for barcode in barcodes:
        item = items_map.get(barcode.id)
        nt = non_tray_items_map.get(barcode.id)
        if item or nt:
            log_audit_event(
                session,
                AuditEventType.ITEM_ADDED,
                f"Item {barcode.value} added to Refile Job {job_id}",
                job_type="refile_jobs",
                job_id=job_id,
                entity_type="items" if item else "non_tray_items",
                entity_id=item.id if item else nt.id,
            )
    session.commit()

    if not refile_job.items and not refile_job.non_tray_items:
        return refile_job
    return sorted_requests(session, refile_job)


@router.delete("/{job_id}/remove_items", response_model=RefileJobDetailOutput, dependencies=[Depends(RequiresPermission("process_refile_jobs"))])
def remove_item_from_refile_job(
    job_id: int,
    refile_job_input: RefileJobInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Remove an item from a refile job.
    """

    lookup_barcode_values = refile_job_input.barcode_values
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_values:
        raise BadRequest(detail="At least one barcode value must be provided")

    refile_job = session.get(RefileJob, job_id)

    if not refile_job:
        raise NotFound(detail=f"Refile Job ID {job_id} Not Found")
        
    validate_assignment_lock(refile_job, current_user.id)

    # V2 FIX
    barcodes = (
        session.execute(select(Barcode).filter(Barcode.value.in_(lookup_barcode_values)))
        .scalars()
        .all()
    )
    
    for barcode in barcodes:
        # V2 FIX
        item = session.execute(select(Item).filter(Item.barcode_id == barcode.id)).scalars().first()
        non_tray_item = None
        if not item:
            non_tray_item = session.execute(select(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id)).scalars().first()

        if item:
            # V2 FIX
            refile_item = (
                session.execute(select(RefileItem)
                .filter(
                    RefileItem.refile_job_id == job_id, RefileItem.item_id == item.id
                ))
                .scalars()
                .first()
            )

            if refile_item:
                session.delete(refile_item)
                item.scanned_for_refile_queue = True
                item.scanned_for_refile = False
                item.scanned_for_refile_dt = None
                item.update_dt = update_dt
        elif non_tray_item:
            # V2 FIX
            refile_non_tray_item = (
                session.execute(select(RefileNonTrayItem)
                .filter(
                    RefileNonTrayItem.refile_job_id == job_id,
                    RefileNonTrayItem.non_tray_item_id == non_tray_item.id,
                ))
                .scalars()
                .first()
            )

            if refile_non_tray_item:
                session.delete(refile_non_tray_item)
                non_tray_item.scanned_for_refile_queue = True
                non_tray_item.scanned_for_refile = False
                non_tray_item.scanned_for_refile_dt = None
                non_tray_item.update_dt = update_dt

    session.commit()
    session.refresh(refile_job)

    if not refile_job.items and not refile_job.non_tray_items:
        return refile_job
    return sorted_requests(session, refile_job)


@router.patch("/{job_id}/update_item/{item_id}", response_model=RefileJobDetailOutput, dependencies=[Depends(RequiresPermission("process_refile_jobs"))])
def update_item_in_refile_job(
    job_id: int,
    item_id: int,
    refile_job_item_input: ItemUpdateInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Update an item in a refile job.
    """

    refile_job = session.get(RefileJob, job_id)

    if not refile_job:
        raise NotFound(detail=f"Refile Job ID {job_id} not found")
        
    validate_assignment_lock(refile_job, current_user.id)

    # V2 FIX
    existing_item = session.execute(select(Item).filter(Item.id == item_id)).scalars().first()

    if not existing_item:
        raise NotFound(detail=f"Item ID {item_id} not found")

    # Update the item record with the mutated data
    update_dt = datetime.now(timezone.utc)
    setattr(existing_item, "update_dt", update_dt)
    setattr(existing_item, "status", "In")
    setattr(existing_item, "scanned_for_refile", True)
    setattr(existing_item, "scanned_for_refile_dt", update_dt)
    setattr(existing_item, "shipping_bin_id", None)
    setattr(existing_item, "scanned_for_shipping", False)
    session.add(existing_item)
    session.commit()

    item_barcode = existing_item.barcode.value if existing_item.barcode else str(item_id)
    tray_barcode = existing_item.tray.barcode.value if existing_item.tray and existing_item.tray.barcode else "Unknown Tray"
    log_audit_event(
        session,
        AuditEventType.ITEM_REFILED,
        f"Item {item_barcode} refiled to Tray {tray_barcode}",
        job_type="refile_jobs",
        job_id=job_id,
        entity_type="items",
        entity_id=item_id,
    )
    session.commit()

    session.refresh(refile_job)

    if not refile_job.items and not refile_job.non_tray_items:
        return refile_job
    return sorted_requests(session, refile_job)


@router.patch(
    "/{job_id}/update_non_tray_items/{non_tray_item_id}",
    response_model=RefileJobDetailOutput,
    dependencies=[Depends(RequiresPermission("process_refile_jobs"))]
)
def update_non_tray_item_in_refile_job(
    job_id: int,
    non_tray_item_id: int,
    refile_job_non_tray_item_input: NonTrayItemUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a Non Tray item in a refile job.
    """

    refile_job = session.get(RefileJob, job_id)

    if not refile_job:
        raise NotFound(detail=f"Refile Job ID {job_id} not found")

    # V2 FIX
    existing_item = (
        session.execute(select(NonTrayItem).filter(NonTrayItem.id == non_tray_item_id))
        .scalars()
        .first()
    )

    if not existing_item:
        raise NotFound(detail=f"Non Tray Item ID {non_tray_item_id} not found")

    # Update the item record with the mutated data
    update_dt = datetime.now(timezone.utc)

    setattr(existing_item, "update_dt", update_dt)
    setattr(existing_item, "status", "In")
    setattr(existing_item, "scanned_for_refile", True)
    setattr(existing_item, "scanned_for_refile_dt", update_dt)
    setattr(existing_item, "shipping_bin_id", None)
    setattr(existing_item, "scanned_for_shipping", False)
    session.add(existing_item)
    session.commit()

    item_barcode = existing_item.barcode.value if existing_item.barcode else str(non_tray_item_id)
    location = existing_item.shelf_position.location if existing_item.shelf_position else "Unknown Location"
    
    log_audit_event(
        session,
        AuditEventType.ITEM_REFILED,
        f"Non-tray item {item_barcode} refiled to Shelf Position {location}",
        job_type="refile_jobs",
        job_id=job_id,
        entity_type="non_tray_items",
        entity_id=non_tray_item_id,
    )
    session.commit()

    session.refresh(refile_job)

    if not refile_job.items and not refile_job.non_tray_items:
        return refile_job
    return sorted_requests(session, refile_job)