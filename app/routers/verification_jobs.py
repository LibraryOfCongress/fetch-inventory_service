# /code/app/routers/verification_jobs.py - REFACRORED TO SQLALCHEMY V2

import logging
from typing import List, Optional

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, func, distinct, case, literal_column, update, and_ # select/update/func imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased, selectinload 

from app.database.session import get_session, commit_record
from app.filter_params import SortParams, JobFilterParams
from app.models.barcodes import Barcode
from app.models.container_types import ContainerType
from app.models.items import Item, ILSSyncState
from app.models.non_tray_items import NonTrayItem
from app.models.trays import Tray
from app.models.users import User
from app.models.verification_changes import VerificationChange
from app.models.verification_jobs import VerificationJob
from app.models.accession_jobs import AccessionJob
from app.schemas.verification_jobs import (
    VerificationJobInput,
    VerificationJobUpdateInput,
    VerificationJobListOutput,
    VerificationJobListDropdownOutput,
    VerificationJobDetailOutput,
    VerificationJobAddInput,
    VerificationJobRemoveInput,
    VerificationJobAccCheckOutput
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter
from app.tasks import (
    complete_verification_job,
    manage_verification_job_transition, manage_verification_job_change_action,
)

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.utils.job_assignment import auto_assign_on_start, update_status_on_assignment, validate_assignment_lock
from app.services.audit_service import log_audit_event, AuditEventType

router = APIRouter(
    prefix="/verification-jobs",
    tags=["verification jobs"],
    dependencies=[Depends(RequiresPermission("can_access_verification"))],
)


@router.get("/", response_model=Page[VerificationJobListOutput])
def get_verification_job_list(
    unshelved: bool | None = False,
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of verification jobs.
    """
    # Use selectinload to fetch related user data in a single, efficient second query.
    query = select(VerificationJob).options(
        selectinload(VerificationJob.assigned_user),
        selectinload(VerificationJob.created_by)
    )

    if unshelved:
        # Retrieve completed verification jobs that have at least one unshelved container
        # A verification job is shelv-able if:
        # 1. It's Completed
        # 2. It has at least one tray or non-tray item without a shelf_position_id
        
        # Subquery for trays with no shelf position
        unshelved_trays = (
            select(Tray.verification_job_id)
            .where(Tray.shelf_position_id == None)
            .where(Tray.verification_job_id != None)
            .distinct()
        )
        
        # Subquery for non-tray items with no shelf position
        unshelved_non_trays = (
            select(NonTrayItem.verification_job_id)
            .where(NonTrayItem.shelf_position_id == None)
            .where(NonTrayItem.verification_job_id != None)
            .distinct()
        )
        
        query = query.where(
            VerificationJob.status == "Completed"
        ).where(
            (VerificationJob.id.in_(unshelved_trays)) | 
            (VerificationJob.id.in_(unshelved_non_trays))
        )
    if params.queue:
        # filter out completed.  maybe someday hide cancelled.
        query = query.where(VerificationJob.status != "Completed")

    # If no status is provided AND we are not in 'unshelved' or 'queue' mode,
    # DEFAULT to fetching only the active jobs to keep the dashboard fast.
    if params.status and len(list(filter(None, params.status))) > 0:
        query = query.where(VerificationJob.status.in_(params.status))
    elif not unshelved and not params.queue:
        query = query.where(
            VerificationJob.status.in_(["Created", "Paused", "Running"])
        )

    if params.workflow_id:
        query = query.where(VerificationJob.workflow_id == params.workflow_id)
    if params.assigned_user_id:
        query = query.where(VerificationJob.assigned_user_id == params.assigned_user_id)
    if params.assigned_user:
        assigned_user_subquery = (
            select(User.id)
            .where(
                func.concat(User.first_name, ' ', User.last_name).in_(
                    params.assigned_user
                )
            )
            .distinct().scalar_subquery()
        )
        query = query.where(VerificationJob.assigned_user_id.in_(assigned_user_subquery))
    if params.container_type:
        subquery = (
            select(ContainerType.id)
            .where(ContainerType.type == params.container_type)
            .distinct().scalar_subquery()
        )
        query = query.where(VerificationJob.container_type_id == subquery)
    if params.trayed is not None:
        query = query.where(VerificationJob.trayed == params.trayed)
    if params.created_by_id:
        query = query.where(VerificationJob.created_by_id == params.created_by_id)
    if params.from_dt:
        query = query.where(VerificationJob.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(VerificationJob.create_dt <= params.to_dt)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(VerificationJob)
        query = sorter.apply_sorting(query, sort_params)
    else:
        # Add a default sort for consistent ordering
        query = query.order_by(VerificationJob.id.desc())

    return paginate(session, query)


@router.get("/dropdown/", response_model=Page[VerificationJobListDropdownOutput])
def get_verification_job_list_lite(
    unshelved: bool | None = False,
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends()
) -> list:
    filtered_jobs_cte = (
        select(VerificationJob)
        .where(
            VerificationJob.shelving_job_id == None,
            VerificationJob.status == "Completed"
        )
        .cte("filtered_jobs")
    )

    VJ = aliased(filtered_jobs_cte)

    tray_count_subq = (
        select(func.count())
        .select_from(Tray)
        .where(Tray.verification_job_id == VJ.c.id)
        .correlate(filtered_jobs_cte)
        .scalar_subquery()
    )

    item_count_subq = (
        select(func.count())
        .select_from(Item)
        .where(Item.verification_job_id == VJ.c.id)
        .correlate(filtered_jobs_cte)
        .scalar_subquery()
    )

    non_tray_item_count_subq = (
        select(func.count())
        .select_from(NonTrayItem)
        .where(NonTrayItem.verification_job_id == VJ.c.id)
        .correlate(filtered_jobs_cte)
        .scalar_subquery()
    )

    query = (
        select(
            VJ.c.id,
            VJ.c.workflow_id,
            VJ.c.trayed,
            tray_count_subq.label("tray_count"),
            item_count_subq.label("item_count"),
            non_tray_item_count_subq.label("non_tray_item_count"),
        )
        .order_by(VJ.c.workflow_id.asc())
    )

    # CRITICAL FIX: Paginate now takes only the query object
    return paginate(session, query)


@router.get("/{id}", response_model=VerificationJobDetailOutput)
def get_verification_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the verification job detail for the given ID.
    """
    verification_job = session.get(VerificationJob, id)

    if verification_job:
        return verification_job

    raise NotFound(detail=f"Verification Job ID {id} Not Found")


@router.get("/by-accession-job-id/{id}", response_model=VerificationJobAccCheckOutput)
def get_verification_job_id_by_acc_job_id(id: int, session: Session = Depends(get_session)):
    """
    This is a quick check endpoint to help the front-end determine if
    an Accession Job has been lost in limbo when Verification Job transition
    fails to fire off.
    """
    # V2 FIX: session.exec().first() -> session.execute(select(...)).scalars().first()
    verification_job = session.execute(
        select(VerificationJob).where(VerificationJob.accession_job_id == id)
    ).scalars().first()
    if verification_job:
        return verification_job

    raise NotFound(detail=f"No Verification Job found for Accession Job id {id}")


@router.get("/workflow/{id}", response_model=VerificationJobDetailOutput)
def get_verification_job_detail_by_workflow(
    id: int, session: Session = Depends(get_session)
):
    """
    Retrieves the verification job detail for the given workflow ID.
    """
    # V2 FIX: session.exec().first() -> session.execute(select(...)).scalars().first()
    verification_job = session.execute(
        select(VerificationJob).where(VerificationJob.workflow_id == id)
    ).scalars().first()

    if verification_job:
        return verification_job

    raise NotFound(detail=f"Verification Job ID {id} Not Found")


@router.post("/", response_model=VerificationJobDetailOutput, status_code=201,
             dependencies=[Depends(RequiresPermission("can_access_verification"))])
def create_verification_job(
    verification_job_input: VerificationJobInput,
    session: Session = Depends(get_session),
):
    """
    Create a new verification job:
    """
    try:
        verification_job = VerificationJob(**verification_job_input.model_dump())

        session.add(verification_job)
        session.commit()
        session.refresh(verification_job)

        log_audit_event(
            session,
            AuditEventType.JOB_CREATED,
            f"Verification Job {verification_job.id} created",
            job_type="verification_jobs",
            job_id=verification_job.id,
        )
        session.commit()

        return verification_job

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=VerificationJobDetailOutput,
              dependencies=[Depends(RequiresPermission("can_access_verification"))])
def update_verification_job(
    id: int,
    verification_job: VerificationJobUpdateInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Update a verification job.
    
    Includes auto-assignment logic:
    - When a user starts a job (status → Running), auto-assign to them if unassigned
    - Prevent users from starting jobs assigned to others
    - When manager assigns a user, auto-update status to Assigned
    """
    try:
        existing_verification_job = session.get(VerificationJob, id)

        # Check if the tray record exists
        if not existing_verification_job:
            raise NotFound(detail=f"Verification Job ID {id} Not Found")

        # capture original status for process check
        original_status = existing_verification_job.status
        original_assigned_user_id = existing_verification_job.assigned_user_id

        # Update the tray record with the mutated data
        mutated_data = verification_job.model_dump(exclude_unset=True)

        # Bblock completion while any item on this job still has a failed ILS
        # lookup (ils_sync_state == SYNC_ERROR).
        if mutated_data.get("status") == "Completed":
            failed_lookup_barcodes = list(session.execute(
                select(Barcode.value)
                .join(Item, Item.barcode_id == Barcode.id)
                .where(
                    Item.verification_job_id == id,
                    Item.ils_sync_state == ILSSyncState.SYNC_ERROR,
                )
            ).scalars().all())
            failed_lookup_barcodes += list(session.execute(
                select(Barcode.value)
                .join(NonTrayItem, NonTrayItem.barcode_id == Barcode.id)
                .where(
                    NonTrayItem.verification_job_id == id,
                    NonTrayItem.ils_sync_state == ILSSyncState.SYNC_ERROR,
                )
            ).scalars().all())

            if failed_lookup_barcodes:
                raise ValidationException(
                    detail=(
                        f"Cannot complete Verification Job {id}: item(s) with a "
                        f"failed ILS lookup remain: {', '.join(failed_lookup_barcodes)}"
                    )
                )

        # Handle auto-assignment when user starts job
        new_status = mutated_data.get("status")
        if new_status:
            auto_assign_on_start(
                existing_verification_job, 
                new_status, 
                current_user.id
            )
        
        # Handle status update when manager assigns user
        new_assigned_user_id = mutated_data.get("assigned_user_id")
        if new_assigned_user_id is not None and "status" not in mutated_data:
            update_status_on_assignment(
                existing_verification_job,
                new_assigned_user_id,
                original_status
            )

        for key, value in mutated_data.items():
            if (key in ["media_type_id", "size_class_id"] and
                existing_verification_job.__getattribute__(key) != value):
                audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"}).copy()
                background_tasks.add_task(
                    manage_verification_job_change_action(
                        existing_verification_job,
                        key,
                        value,
                        audit_info=audit_info
                    )
                )

            setattr(existing_verification_job, key, value)

        setattr(existing_verification_job, "update_dt", datetime.now(timezone.utc))

        existing_verification_job = commit_record(session, existing_verification_job)

        # Log status change if status was updated
        new_status_val = mutated_data.get("status")
        if new_status_val and new_status_val != original_status:
            log_audit_event(
                session,
                AuditEventType.JOB_STATUS_CHANGED,
                f"Status changed from {original_status} to {new_status_val}",
                job_type="verification_jobs",
                job_id=id,
            )
            session.commit()

        if mutated_data.get("status") == "Completed":
            audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"}).copy()
            background_tasks.add_task(
                complete_verification_job,
                existing_verification_job.id,
                original_status,
                audit_info=audit_info
            )
            session.refresh(existing_verification_job)
        else:
            audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"}).copy()
            background_tasks.add_task(
                manage_verification_job_transition,
                existing_verification_job,
                original_status,
                audit_info=audit_info
            )

            session.refresh(existing_verification_job)

        return existing_verification_job

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_cancel_verification_job"))])
def delete_verification_job(id: int, session: Session = Depends(get_session)):
    """
    Delete a verification job by its ID.
    """
    verification_job = session.get(VerificationJob, id)

    if verification_job:
        # do not allow deletion of completed jobs
        if verification_job.status == 'Completed':
            return HTTPException(
                status_code=400,
                detail=f"Verification Job id {id} is complete. Can't delete or cancel completed jobs.",
            )

        # find and reset underlying accession job
        acc_job = session.get(AccessionJob, verification_job.accession_job_id)
        acc_job.status = 'Paused'
        session.add(acc_job)

        if verification_job.container_type_id == 1:
            # V2 FIX: session.exec().all() -> session.execute(select(...)).scalars().all()
            trays_in_ver_job_query = select(Tray).where(Tray.verification_job_id == id)
            trays = session.execute(trays_in_ver_job_query).scalars().all()
            for tray in trays:
                tray.scanned_for_verification = False
                tray.verification_job_id = None
                tray.collection_verified = False
                session.add(tray)
                # V2 FIX: session.exec().all() -> session.execute(select(...)).scalars().all()
                for item in session.execute(select(Item).where(Item.verification_job_id == id)).scalars().all():
                    item.scanned_for_verification = False
                    item.verification_job_id = None
                    session.add(item)
        else:
            # V2 FIX
            non_trays_in_ver_job_query = select(NonTrayItem).where(
                NonTrayItem.verification_job_id == id
            )
            non_tray_items = session.execute(non_trays_in_ver_job_query).scalars().all()
            for non_tray_item in non_tray_items:
                non_tray_item.scanned_for_verification = False
                non_tray_item.verification_job_id = None
                session.add(non_tray_item)

        try:
            session.commit()
        except HTTPException:
            raise
        except Exception as e:
            return HTTPException(
                status_code=500,
                detail=f"{e}",
            )

        session.delete(verification_job)

        log_audit_event(
            session,
            AuditEventType.JOB_DELETED,
            f"Verification Job {id} deleted",
            job_type="verification_jobs",
            job_id=id,
        )
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Verification Job ID {id} Not Found")


@router.patch("/{id}/add", response_model=VerificationJobDetailOutput,
              dependencies=[Depends(RequiresPermission("can_access_verification"))])
def add_item_to_verification_job(
    id: int,
    input: VerificationJobAddInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Add an item to a verification job.
    """

    verification_job = session.get(VerificationJob, id)

    if not verification_job:
        raise NotFound(detail=f"Verification Job ID {id} Not Found")
        
    validate_assignment_lock(verification_job, current_user.id)

    # V2 FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
    barcode = (
        session.execute(select(Barcode).filter(Barcode.value == input.barcode_value))
        .scalars()
        .first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode with value {input.barcode_value} Not Found")

    # V2 FIX
    tray = session.execute(select(Tray).filter(Tray.barcode_id == barcode.id)).scalars().first()
    # V2 FIX
    item = session.execute(select(Item).filter(Item.barcode_id == barcode.id)).scalars().first()
    # V2 FIX
    non_tray_item = (
        session.execute(select(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id))
        .scalars()
        .first()
    )

    if not tray and not item and not non_tray_item:
        raise NotFound(detail=f"Item with barcode value {input.barcode_value} Not "
                              f"Found")
    if tray:
        tray.scanned_for_verification = True
        session.add(tray)
        
        new_verification_changes = []
        items = tray.items
        if items:
            for item in items:
                item.scanned_for_verification = True
                session.add(item)
                
                item_barcode = session.get(Barcode, item.barcode_id)
                new_verification_changes.append(VerificationChange(
                    workflow_id=verification_job.workflow_id,
                    tray_barcode_value=barcode.value,
                    item_barcode_value=item_barcode.value,
                    change_type="Added",
                    completed_by_id=input.user_id
                ))
        session.bulk_save_objects(new_verification_changes)
        session.commit()
    elif item:
        if item.ils_sync_state == ILSSyncState.SYNC_ERROR:
            raise ValidationException(detail=f"ILS Failed Lookup: {barcode.value}")

        item.scanned_for_verification = True
        session.add(item)

        # V2 FIX
        tray_barcode = session.execute(select(Barcode).join(Tray, Barcode.id == Tray.barcode_id).filter(Tray.id == item.tray_id)).scalars().first()
        new_verification_change = VerificationChange(
            workflow_id=verification_job.workflow_id,
            tray_barcode_value=tray_barcode.value,
            item_barcode_value=barcode.value,
            change_type="Added",
            completed_by_id=input.user_id
        )
        commit_record(session, new_verification_change)
    else:
        # See the item branch above -- same ILS-failed-lookup block, same
        # "no mutation" guarantee on rejection.
        if non_tray_item.ils_sync_state == ILSSyncState.SYNC_ERROR:
            raise ValidationException(detail=f"ILS Failed Lookup: {barcode.value}")

        # User requested that adding an item implies it must be scanned again to verify.
        non_tray_item.scanned_for_verification = False
        session.add(non_tray_item)

        
        new_verification_change = VerificationChange(
            workflow_id=verification_job.workflow_id,
            item_barcode_value=barcode.value,
            change_type="Added",
            completed_by_id=input.user_id
        )
        commit_record(session, new_verification_change)

    verification_job.update_dt = datetime.now(timezone.utc)
    session.refresh(verification_job)

    log_audit_event(
        session,
        AuditEventType.ITEM_ADDED,
        f"Item {input.barcode_value} added to Verification Job {id}",
        job_type="verification_jobs",
        job_id=id,
        entity_type="items" if item else ("trays" if tray else "non_tray_items"),
        entity_id=(item.id if item else (tray.id if tray else non_tray_item.id)),
    )
    session.commit()

    return verification_job


@router.patch("/{id}/remove", response_model=VerificationJobDetailOutput,
              dependencies=[Depends(RequiresPermission("can_access_verification"))])
def remove_item_from_verification_job(
    id: int,
    input: VerificationJobRemoveInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Remove an item from a verification job.
    """
    verification_job = session.get(VerificationJob, id)

    if not verification_job:
        raise NotFound(detail=f"Verification Job ID {id} Not Found")
        
    validate_assignment_lock(verification_job, current_user.id)

    # V2 FIX
    barcode = (
        session.execute(select(Barcode).filter(Barcode.value == input.barcode_value))
        .scalars()
        .first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode with value {input.barcode_value} Not Found")

    # V2 FIX
    tray = session.execute(select(Tray).filter(Tray.barcode_id == barcode.id)).scalars().first()
    # V2 FIX
    item = session.execute(select(Item).filter(Item.barcode_id == barcode.id)).scalars().first()
    # V2 FIX
    non_tray_item = (
        session.execute(select(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id))
        .scalars()
        .first()
    )

    if not tray and not item and not non_tray_item:
        raise NotFound(detail=f"Item with barcode value {input.barcode_value} Not "
                              f"Found")
    if tray:
        tray.scanned_for_verification = False
        session.add(tray)
        
        new_verification_changes = []
        items = tray.items
        if items:
            for item in items:
                item.scanned_for_verification = False
                session.add(item)
                
                item_barcode = session.get(Barcode, item.barcode_id)
                new_verification_changes.append(VerificationChange(
                    workflow_id=verification_job.workflow_id,
                    tray_barcode_value=barcode.value,
                    item_barcode_value=item_barcode.value,
                    change_type="Removed",
                    completed_by_id=input.user_id
                ))
        session.bulk_save_objects(new_verification_changes)
        session.commit()
    elif item:
        item.scanned_for_verification = False
        session.add(item)
        
        # V2 FIX
        tray_barcode = session.execute(select(Barcode).join(Tray, Barcode.id == Tray.barcode_id).filter(Tray.id == item.tray_id)).scalars().first()
        new_verification_change = VerificationChange(
            workflow_id=verification_job.workflow_id,
            tray_barcode_value=tray_barcode.value,
            item_barcode_value=barcode.value,
            change_type="Removed",
            completed_by_id=input.user_id
        )
        commit_record(session, new_verification_change)
    else:
        non_tray_item.scanned_for_verification = False
        session.add(non_tray_item)
        
        new_verification_change = VerificationChange(
            workflow_id=verification_job.workflow_id,
            item_barcode_value=barcode.value,
            change_type="Removed",
            completed_by_id=input.user_id
        )
        commit_record(session, new_verification_change)

    verification_job.update_dt = datetime.now(timezone.utc)
    session.refresh(verification_job)

    log_audit_event(
        session,
        AuditEventType.ITEM_REMOVED,
        f"Item {input.barcode_value} removed from Verification Job {id}",
        job_type="verification_jobs",
        job_id=id,
        entity_type="items" if item else ("trays" if tray else "non_tray_items"),
        entity_id=(item.id if item else (tray.id if tray else non_tray_item.id)),
    )
    session.commit()

    return verification_job


@router.delete("/{id}/items/{barcode_value}", response_model=VerificationJobDetailOutput,
                dependencies=[Depends(RequiresPermission("can_access_verification"))])
def delete_item_from_verification_job(
    id: int,
    barcode_value: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Permanently delete the Item/NonTrayItem for the given
    barcode from this Verification Job 
    """
    verification_job = session.get(VerificationJob, id)

    if not verification_job:
        raise NotFound(detail=f"Verification Job ID {id} Not Found")

    validate_assignment_lock(verification_job, current_user.id)

    barcode = (
        session.execute(select(Barcode).filter(Barcode.value == barcode_value))
        .scalars()
        .first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode with value {barcode_value} Not Found")

    item = session.execute(
        select(Item).filter(Item.barcode_id == barcode.id, Item.verification_job_id == id)
    ).scalars().first()
    non_tray_item = session.execute(
        select(NonTrayItem).filter(
            NonTrayItem.barcode_id == barcode.id, NonTrayItem.verification_job_id == id
        )
    ).scalars().first()

    if not item and not non_tray_item:
        raise NotFound(
            detail=f"No item with barcode value {barcode_value} found on "
                   f"Verification Job {id}"
        )

    record = item or non_tray_item
    # Capture identity before delete -- SQLAlchemy expires attributes on
    # commit by default, and re-reading them off a just-deleted row would try
    # (and fail) to re-fetch it from the DB.
    record_id = record.id
    entity_type = "items" if item else "non_tray_items"

    new_verification_change = VerificationChange(
        workflow_id=verification_job.workflow_id,
        item_barcode_value=barcode.value,
        change_type="Removed",
        completed_by_id=current_user.id,
    )
    session.add(new_verification_change)
    session.delete(record)

    try:
        session.flush()
    except IntegrityError as e:
        session.rollback()
        raise ValidationException(
            detail=f"Could not delete item {barcode_value}: {e}"
        )

    log_audit_event(
        session,
        AuditEventType.ENTITY_DELETED,
        f"Item {barcode_value} deleted from Verification Job {id} (ILS failed lookup)",
        job_type="verification_jobs",
        job_id=id,
        entity_type=entity_type,
        entity_id=record_id,
    )

    verification_job.update_dt = datetime.now(timezone.utc)
    session.commit()
    session.refresh(verification_job)

    return verification_job
