# /code/app/routers/shelving_jobs.py - FULL REFACRORED TO SQLALCHEMY V2

import logging
from typing import Optional, List

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session, selectinload # Session and selectinload imported from sqlalchemy.orm now
from sqlalchemy import select, func, update, delete, or_ # select/update/delete/func/or_ imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.filter_params import SortParams, JobFilterParams
from app.logger import inventory_logger
from app.models.accession_jobs import AccessionJob, AccessionJobStatus
from app.models.users import User
from app.events import update_shelf_space_after_tray, update_shelf_space_after_non_tray
from app.sorting import ShelvingJobSorter
from app.utilities import (
    process_containers_for_shelving,
    manage_transition,
    start_session_with_audit_info,
)
from app.tasks import complete_shelving_job, process_tray_item_move
from app.models.verification_jobs import VerificationJob, VerificationJobStatus
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.items import Item
from app.models.shelving_jobs import ShelvingJob, ShelvingJobStatus
from app.models.shelves import Shelf
from app.models.shelf_positions import ShelfPosition
from app.models.barcodes import Barcode
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.models.owners import Owner
from app.models.size_class import SizeClass
from app.models.shelf_types import ShelfType
from app.schemas.shelving_jobs import (
    ShelvingJobInput,
    ShelvingJobUpdateInput,
    ShelvingJobListOutput,
    ShelvingJobDetailOutput,
    ReAssignmentInput,
    ReAssignmentOutput, ProposedReAssignmentInput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
    BadRequest,
)
from app.helpers.owner_helpers import is_child_of_owner
from app.helpers.system_setting_helpers import get_setting_value

logger = logging.getLogger(__name__)

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.utils.job_assignment import auto_assign_on_start, update_status_on_assignment, validate_assignment_lock
from app.utils.container_status import passes_job_gate
from app.services.audit_service import log_audit_event, AuditEventType

router = APIRouter(
    prefix="/shelving-jobs",
    tags=["shelving jobs"],
)


def get_shelving_position(session: Session, shelving_job: ShelvingJob):
    trays = shelving_job.trays
    non_tray_items = shelving_job.non_tray_items

    if trays:
        for index, tray in enumerate(trays):
            if not tray.shelf_position_id and tray.shelf_position_proposed_id:
                # V2 FIX: session.query().where().first() -> session.execute(select(...)).scalars().first()
                trays[index].shelf_position = (
                    session.execute(select(ShelfPosition)
                    .where(tray.shelf_position_proposed_id == ShelfPosition.id))
                    .scalars()
                    .first()
                )
            else:
                continue

    if non_tray_items:
        for index, non_tray_item in enumerate(non_tray_items):
            if (
                not non_tray_item.shelf_position_id
                and non_tray_item.shelf_position_proposed_id
            ):
                # V2 FIX
                non_tray_items[index].shelf_position = (
                    session.execute(select(ShelfPosition)
                    .where(non_tray_item.shelf_position_proposed_id == ShelfPosition.id))
                    .scalars()
                    .first()
                )
            else:
                continue

    shelving_job.trays = trays
    shelving_job.non_tray_items = non_tray_items

    return shelving_job


def _create_or_get_shelving_container(
    session: Session,
    shelving_job_id: int,
    tray: Optional[Tray] = None,
    non_tray_item: Optional[NonTrayItem] = None,
    shelf_position: Optional[ShelfPosition] = None,
    status: str = "Shelved"
):
    """
    Create or get existing ShelvingJobContainer record.
    Used to unify container tracking across Direct to Shelf and Shelve by List workflows.
    """
    from app.models.shelving_job_containers import (
        ShelvingJobContainer,
        ShelvingJobContainerStatus
    )
    
    # Map status string to proper status
    status_value = status if status else ShelvingJobContainerStatus.SHELVED
    
    # Check for existing container entry
    if tray:
        existing = session.execute(
            select(ShelvingJobContainer)
            .where(ShelvingJobContainer.shelving_job_id == shelving_job_id)
            .where(ShelvingJobContainer.tray_id == tray.id)
        ).scalars().first()
    else:
        existing = session.execute(
            select(ShelvingJobContainer)
            .where(ShelvingJobContainer.shelving_job_id == shelving_job_id)
            .where(ShelvingJobContainer.non_tray_item_id == non_tray_item.id)
        ).scalars().first()
    
    if existing:
        # Update existing record
        existing.actual_shelf_position_id = shelf_position.id if shelf_position else None
        existing.shelved_dt = datetime.now(timezone.utc)
        existing.status = status_value
        session.add(existing)
        return existing
    
    # Create new record
    container = ShelvingJobContainer(
        shelving_job_id=shelving_job_id,
        tray_id=tray.id if tray else None,
        non_tray_item_id=non_tray_item.id if non_tray_item else None,
        actual_shelf_position_id=shelf_position.id if shelf_position else None,
        shelved_dt=datetime.now(timezone.utc),
        status=status_value
    )
    session.add(container)
    return container


@router.get("/", response_model=Page[ShelvingJobListOutput], dependencies=[Depends(RequiresPermission("can_access_shelving"))])
def get_shelving_job_list(
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Retrieve a paginated list of shelving jobs.
    """
    # Create a query to select all Shelving Job with eager loading for dashboard fields
    query = select(ShelvingJob).options(
        selectinload(ShelvingJob.assigned_user),
        selectinload(ShelvingJob.created_by),
        selectinload(ShelvingJob.building)
    )

    try:
        if params.queue:
            query = query.where(ShelvingJob.status != "Completed").where(
                ShelvingJob.status != "Cancelled"
            )
        if params.status and len(list(filter(None, params.status))) > 0:
            query = query.where(ShelvingJob.status.in_(params.status))
        if params.workflow_id:
            query = query.where(ShelvingJob.id == params.workflow_id)
        if params.assigned_user_id:
            query = query.where(ShelvingJob.assigned_user_id == params.assigned_user_id)
        if params.assigned_user:
            assigned_user_subquery = (
                select(User.id)
                .where(
                    func.concat(User.first_name, " ", User.last_name).in_(
                        params.assigned_user
                    )
                )
                .distinct().scalar_subquery()
            )
            query = query.where(ShelvingJob.assigned_user_id.in_(assigned_user_subquery))
        if params.created_by_id:
            query = query.where(ShelvingJob.created_by_id == params.created_by_id)
        if params.from_dt:
            query = query.where(ShelvingJob.create_dt >= params.from_dt)
        if params.to_dt:
            query = query.where(ShelvingJob.create_dt <= params.to_dt)

        # Validate and Apply sorting based on sort_params
        if sort_params.sort_by:
            # Apply sorting using RequestSorter
            sorter = ShelvingJobSorter(ShelvingJob)
            query = sorter.apply_sorting(query, sort_params)

        return paginate(session, query)

    except IntegrityError as e:
        raise InternalServerError(detail=f"{e}")


@router.get("/{id}", response_model=ShelvingJobDetailOutput, dependencies=[Depends(RequiresPermission("can_access_shelving"))])
def get_shelving_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the shelving job detail for the given ID.
    """
    shelving_job = session.get(ShelvingJob, id)

    if shelving_job:
        return get_shelving_position(session, shelving_job)

    raise NotFound(detail=f"Shelving Job ID {id} Not Found")


@router.post("/", response_model=ShelvingJobDetailOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))])
def create_shelving_job(
    shelving_job_input: ShelvingJobInput,
    session: Session = Depends(get_session),
) -> ShelvingJob:
    """
    Create a new shelving job.
    
    - origin='Direct': Creates a Direct to Shelf job (containers added during execution)
    - origin='List': Creates a Shelve by List job (optionally populates from verification_job_ids)
    """
    try:
        # Create the base shelving job
        new_job = ShelvingJob(
            origin=OriginStatus[shelving_job_input.origin],
            mode=ShelvingMode[shelving_job_input.mode] if shelving_job_input.mode else ShelvingMode.Manual,
            building_id=shelving_job_input.building_id,
            created_by_id=shelving_job_input.created_by_id,
            assigned_user_id=shelving_job_input.assigned_user_id,
            allow_unassigned_size=shelving_job_input.allow_unassigned_size,
            allow_unassigned_owner=shelving_job_input.allow_unassigned_owner,
            allow_tiered_owner=shelving_job_input.allow_tiered_owner,
            status=ShelvingJobStatus.Created,
        )
        session.add(new_job)
        session.commit()
        session.refresh(new_job)

        # For List origin, optionally populate containers from verification jobs
        if shelving_job_input.origin == "List" and shelving_job_input.verification_job_ids:
            added_count = 0
            skipped_barcodes = []
            
            for vj_id in shelving_job_input.verification_job_ids:
                verification_job = session.get(VerificationJob, vj_id)
                if not verification_job:
                    logger.warning(f"Verification job {vj_id} not found")
                    continue
                if verification_job.status != VerificationJobStatus.Completed:
                    logger.warning(f"Verification job {vj_id} is not Completed, skipping")
                    continue
                
                # Query trays by verification_job_id
                trays = session.execute(
                    select(Tray).where(Tray.verification_job_id == vj_id)
                ).scalars().all()
                
                for tray in trays:
                    # Skip if already shelved
                    if tray.shelf_position_id:
                        skipped_barcodes.append(tray.barcode.value if tray.barcode else f"TRAY-{tray.id}")
                        continue
                    
                    # Check if already on another active shelving job
                    existing = session.execute(
                        select(ShelvingJobContainer)
                        .join(ShelvingJob)
                        .where(
                            ShelvingJobContainer.tray_id == tray.id,
                            ShelvingJob.status.in_([
                                ShelvingJobStatus.Created,
                                ShelvingJobStatus.Running,
                                ShelvingJobStatus.Paused
                            ])
                        )
                    ).scalars().first()
                    
                    if existing:
                        skipped_barcodes.append(tray.barcode.value if tray.barcode else f"TRAY-{tray.id}")
                        continue
                    
                    container = ShelvingJobContainer(
                        shelving_job_id=new_job.id,
                        tray_id=tray.id,
                        status=ShelvingJobContainerStatus.PENDING
                    )
                    session.add(container)
                    added_count += 1
                
                # Query non-tray items by verification_job_id
                non_tray_items = session.execute(
                    select(NonTrayItem).where(NonTrayItem.verification_job_id == vj_id)
                ).scalars().all()
                
                for nti in non_tray_items:
                    # Skip if already shelved
                    if nti.shelf_position_id:
                        skipped_barcodes.append(nti.barcode.value if nti.barcode else f"NTI-{nti.id}")
                        continue
                    
                    # Check if already on another active shelving job
                    existing = session.execute(
                        select(ShelvingJobContainer)
                        .join(ShelvingJob)
                        .where(
                            ShelvingJobContainer.non_tray_item_id == nti.id,
                            ShelvingJob.status.in_([
                                ShelvingJobStatus.Created,
                                ShelvingJobStatus.Running,
                                ShelvingJobStatus.Paused
                            ])
                        )
                    ).scalars().first()
                    
                    if existing:
                        skipped_barcodes.append(nti.barcode.value if nti.barcode else f"NTI-{nti.id}")
                        continue
                    
                    container = ShelvingJobContainer(
                        shelving_job_id=new_job.id,
                        non_tray_item_id=nti.id,
                        status=ShelvingJobContainerStatus.PENDING
                    )
                    session.add(container)
                    added_count += 1
            
            session.commit()
            logger.info(f"Created List job {new_job.id} with {added_count} containers, skipped {len(skipped_barcodes)}")

        # For Direct origin, job is created empty - containers added during execution
        session.refresh(new_job)

        log_audit_event(
            session,
            AuditEventType.JOB_CREATED,
            f"Shelving Job {new_job.id} created (origin={shelving_job_input.origin})",
            job_type="shelving_jobs",
            job_id=new_job.id,
        )
        session.commit()

        return get_shelving_position(session, new_job)

    except IntegrityError as e:
        session.rollback()
        raise ValidationException(detail=f"Integrity Error: {e.orig}")
    except ValidationException as e:
        session.rollback()
        raise ValidationException(detail=f"{e.detail}")
    except NotFound as e:
        session.rollback()
        raise NotFound(detail=f"{e.detail}")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise InternalServerError(detail=str(e))


@router.patch("/{id}", response_model=ShelvingJobDetailOutput, dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))])
def update_shelving_job(
    id: int,
    shelving_job: ShelvingJobUpdateInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Update an existing shelving job with the provided data.
    
    Includes auto-assignment logic:
    - When a user starts a job (status → Running), auto-assign to them if unassigned
    - Prevent users from starting jobs assigned to others
    - When manager assigns a user, auto-update status to Assigned
    """
    try:
        existing_shelving_job = session.get(ShelvingJob, id)

        if not existing_shelving_job:
            raise NotFound(detail=f"Shelving Job ID {id} Not Found")

        # Capture original status before changes
        original_status = existing_shelving_job.status
        original_assigned_user_id = existing_shelving_job.assigned_user_id
        
        # Handle auto-assignment when user starts job
        if shelving_job.status:
            auto_assign_on_start(
                existing_shelving_job, 
                shelving_job.status, 
                current_user.id
            )
        
        # Handle status update when manager assigns user
        if shelving_job.assigned_user_id is not None and not shelving_job.status:
            update_status_on_assignment(
                existing_shelving_job,
                shelving_job.assigned_user_id,
                original_status
            )

        if shelving_job.status and shelving_job.run_timestamp:
            existing_shelving_job = manage_transition(
                existing_shelving_job, shelving_job
            )

        mutated_data = shelving_job.model_dump(
            exclude_unset=True, exclude={"run_timestamp"}
        )

        for key, value in mutated_data.items():
            setattr(existing_shelving_job, key, value)

        setattr(existing_shelving_job, "update_dt", datetime.now(timezone.utc))

        if mutated_data.get("status") == "Completed":
            audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"}).copy()
            background_tasks.add_task(
                complete_shelving_job,
                existing_shelving_job.id,
                audit_info=audit_info
            )

        session.add(existing_shelving_job)
        session.commit()
        session.refresh(existing_shelving_job)

        # Log status change if status was updated
        new_status_val = mutated_data.get("status")
        if new_status_val and str(new_status_val) != str(original_status):
            log_audit_event(
                session,
                AuditEventType.JOB_STATUS_CHANGED,
                f"Status changed from {original_status} to {new_status_val}",
                job_type="shelving_jobs",
                job_id=id,
            )
            session.commit()

        target_assigned_user = (
            shelving_job.assigned_user_id
            if shelving_job.assigned_user_id is not None
            else getattr(existing_shelving_job, "assigned_user_id", None)
        )

        if original_assigned_user_id != target_assigned_user:
            user_msg = "Reassigned" if original_assigned_user_id else "Assigned"
            if target_assigned_user:
                assigned_to_user = session.get(User, target_assigned_user)
                assigned_name = assigned_to_user.first_name + " " + assigned_to_user.last_name if assigned_to_user else str(target_assigned_user)
                log_audit_event(
                    session,
                    AuditEventType.JOB_ASSIGNED,
                    f"Shelving Job {id} {user_msg.lower()} to {assigned_name}",
                    job_type="shelving_jobs",
                    job_id=id,
                )
            else:
                log_audit_event(
                    session,
                    AuditEventType.JOB_ASSIGNED,
                    f"Shelving Job {id} unassigned",
                    job_type="shelving_jobs",
                    job_id=id,
                )
            session.commit()

        return get_shelving_position(session, existing_shelving_job)

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", status_code=204, dependencies=[Depends(RequiresPermission("delete_shelving_jobs"))])
def delete_shelving_job(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelving job by its ID.
    """
    shelving_job = session.get(ShelvingJob, id)
    if shelving_job.status in ["Running", "Completed"]:
        raise ValidationException(
            detail=f"""Shelving Job ID {id} status is in "
                                         'Running' or 'Completed'"""
        )

    if shelving_job:
        trays = shelving_job.trays
        non_tray_items = shelving_job.non_tray_items
        update_dt = datetime.now(timezone.utc)

        if trays:
            tray_ids = [tray.id for tray in trays]
            if tray_ids:
                # V2 UPDATE FIX
                session.execute(
                    update(Tray).where(Tray.id.in_(tray_ids)).values(
                        shelving_job_id=None,
                        shelf_position_id=None,
                        shelf_position_proposed_id=None,
                        shelved_dt=None,
                        update_dt=update_dt,
                    )
                )

        if non_tray_items:
            non_tray_item_ids = [non_tray_item.id for non_tray_item in non_tray_items]
            if non_tray_item_ids:
                # V2 UPDATE FIX
                session.execute(
                    update(NonTrayItem).where(NonTrayItem.id.in_(non_tray_item_ids)).values(
                        shelving_job_id=None,
                        shelf_position_id=None,
                        shelf_position_proposed_id=None,
                        shelved_dt=None,
                        update_dt=update_dt,
                    )
                )

        # Updating Verifications Jobs
        # V2 FIX: session.query().where().all() -> session.execute(select(...)).scalars().all()
        existing_verification_jobs = (
            session.execute(select(VerificationJob)
            .where(VerificationJob.shelving_job_id == id))
            .scalars()
            .all()
        )

        if existing_verification_jobs:
            verification_job_ids = [
                verification_job.id for verification_job in existing_verification_jobs
            ]
            if verification_job_ids:
                # V2 UPDATE FIX
                session.execute(
                    update(VerificationJob).where(VerificationJob.id.in_(verification_job_ids))
                    .values(shelving_job_id=None, update_dt=update_dt)
                )

        # Removing Shelving Job Discrepancies
        # V2 FIX: session.query().where().all() -> session.execute(select(...)).scalars().all()
        existing_shelving_job_discrepancies = (
            session.execute(select(ShelvingJobDiscrepancy)
            .where(ShelvingJobDiscrepancy.shelving_job_id == id))
            .scalars()
            .all()
        )

        if existing_shelving_job_discrepancies:
            discrepancy_ids = [
                discrepancy.id for discrepancy in existing_shelving_job_discrepancies
            ]
            if discrepancy_ids:
                # V2 DELETE FIX: session.query().filter().delete() -> session.execute(delete(Model).where(conditions))
                session.execute(
                    delete(ShelvingJobDiscrepancy)
                    .where(ShelvingJobDiscrepancy.id.in_(discrepancy_ids))
                )

        log_audit_event(
            session,
            AuditEventType.JOB_DELETED,
            f"Shelving Job {id} deleted",
            job_type="shelving_jobs",
            job_id=id,
        )
        session.delete(shelving_job)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Shelving Job ID {id} Not Found")


@router.post("/{id}/reassign-container-location", response_model=ReAssignmentOutput, dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))])
def reassign_container_location(
    id: int,
    reassignment_input: ReAssignmentInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Re-Assign container shelf position OR Move Item to Tray, given a container id/barcode.
    Supports unified shelving and move operations.
    """
    shelving_job = session.get(ShelvingJob, id)
    if not shelving_job:
        raise NotFound(detail=f"Shelving Job ID {id} Not Found")
        
    validate_assignment_lock(shelving_job, current_user.id)
    
    audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
    
    # ---------------------------------------------------------
    # 1. Identify the Source Container (Tray, NonTrayItem, or Item)
    # ---------------------------------------------------------
    container = None
    container_type = None  # "Tray", "NonTrayItem", "Item"
    
    if reassignment_input.container_id:
        if reassignment_input.trayed is not None:
            if reassignment_input.trayed:
                container = session.get(Tray, reassignment_input.container_id)
                container_type = "Tray"
            else:
                # Ambiguous: could be NonTrayItem or Item. 
                # If shelving job context (legacy), it's NonTrayItem.
                # If Move-to-Tray, it might be Item.
                # Try NonTrayItem first as per legacy.
                container = session.get(NonTrayItem, reassignment_input.container_id)
                container_type = "NonTrayItem"
                
                # If not found, try Item (for Move Ops)
                if not container:
                    container = session.get(Item, reassignment_input.container_id)
                    container_type = "Item"
        else:
             # Try determining by ID alone (risky, IDs overlap). 
             # Require trayed flag or barcode preferably.
             # If ID passed without type, assume Item or check both?
             # Legacy logic raised ValidationException, but we want flexibility.
             # Let's rely on barcode if ID fails or type missing.
             pass

    if not container and reassignment_input.container_barcode_value:
        # Lookup by Barcode
        barcode_obj = session.execute(
            select(Barcode).where(Barcode.value == reassignment_input.container_barcode_value)
        ).scalars().first()
        
        if barcode_obj:
            # Check Tray
            tray = session.execute(select(Tray).where(Tray.barcode_id == barcode_obj.id)).scalars().first()
            if tray:
                container = tray
                container_type = "Tray"
            else:
                # Check NonTrayItem
                nti = session.execute(select(NonTrayItem).where(NonTrayItem.barcode_id == barcode_obj.id)).scalars().first()
                if nti:
                    container = nti
                    container_type = "NonTrayItem"
                else:
                    # Check Item (Item inside Tray)
                    item = session.execute(select(Item).where(Item.barcode_id == barcode_obj.id)).scalars().first()
                    if item:
                        container = item
                        container_type = "Item"

    if not container:
         raise NotFound(detail=f"Container not found with provided criteria.")

    # ---------------------------------------------------------
    # 2. Handle Move-to-Tray Operation
    # ---------------------------------------------------------
    if reassignment_input.destination_tray_id or reassignment_input.destination_tray_barcode_value:
        if container_type != "Item":
             # Implementing NonTrayItem -> Tray move? 
             # Currently Move-to-Tray only supported for Items (Tray Transfer or Shelf->Tray if implemented)
             # If NonTrayItem, we might need to convert it?
             # NonTrayItem IS an item on shelf. 
             # Currently we treat "Item" model as the master.
             # If input was NTI, we should find the corresponding Item record?
             # Usually NonTrayItem *wraps* the Item? No, separate table.
             # But same barcode.
             # If we move NTI to Tray, we delete NTI and update Item?
             # Complex. Let's assume input is "Item" (scanned barcode resolved to Item).
             pass

        # Destination Tray Lookup
        dest_tray = None
        if reassignment_input.destination_tray_id:
            dest_tray = session.get(Tray, reassignment_input.destination_tray_id)
        elif reassignment_input.destination_tray_barcode_value:
            dest_tray = session.execute(
                select(Tray).join(Barcode).where(Barcode.value == reassignment_input.destination_tray_barcode_value)
            ).scalars().first()
            
        if not dest_tray:
            raise NotFound(detail="Destination Tray not found")

        # Logic for Moving Item to Tray (Inline)
        # Ensure Item matches requirements
        if container_type == "NonTrayItem":
             # Convert NonTrayItem to Item logic?
             # NonTrayItem IS an item on shelf. 
             # Currently we treat "Item" model as the master.
             # If input was NTI, we should find the corresponding Item record?
             # Usually NonTrayItem *wraps* the Item? No, separate table.
             # But same barcode.
             # If we move NTI to Tray, we delete NTI and update Item?
             # Complex. Let's assume input is "Item" (scanned barcode resolved to Item).
             pass

        if container_type == "Item":
             item = container
             # Validations
             if not item.scanned_for_accession or not item.scanned_for_verification:
                  raise ValidationException(detail="Item not accessioned or verified")
             
             src_tray = session.get(Tray, item.tray_id) if item.tray_id else None
             
             # Perform Move
             item.tray_id = dest_tray.id
             item.size_class_id = dest_tray.size_class_id
             item.owner_id = dest_tray.owner_id
             # Copy other props...
             
             # Touch timestamps
             update_dt = datetime.now(timezone.utc)
             item.update_dt = update_dt
             dest_tray.update_dt = update_dt
             
             session.add(item)
             session.add(dest_tray)
             
             # Handle Source Tray cleanup (if empty)
             if src_tray:
                 session.refresh(src_tray) # Update items list
                 if len(src_tray.items) == 0:
                      # Withdraw source tray
                      pass # (Simplified for inline, or rely on task)
             
             # Track in ShelvingJobContainer
             # Create/Update SJC
             # Check if SJC exists for this job/item?
             # Usually we create a NEW SJC for the move action
             sjc = ShelvingJobContainer(
                 shelving_job_id=id,
                 item_id=item.id,
                 destination_tray_id=dest_tray.id,
                 status="Shelved", # or Assiged
                 shelved_dt=update_dt,
                 was_overridden=False # Assuming no overrides in this flow
             )
             session.add(sjc)
             session.commit()
             session.refresh(sjc)
             
             # Construct Output (ReAssignmentOutput)
             # Need to fetch barcode rel
             item_barcode = session.get(Barcode, item.barcode_id) if item.barcode_id else None
             
             return ReAssignmentOutput(
                 id=sjc.id,
                 shelving_job_id=sjc.shelving_job_id,
                 barcode=item_barcode.value if item_barcode else None,
                 container_id=item.id,
                 container_type=container_type,
                 shelf_position_id=None, # Item is in tray, not directly on shelf
                 shelf_position_number=None,
                 shelf_id=None,
                 shelf_barcode_value=None,
                 destination_tray_id=dest_tray.id,
                 destination_tray_barcode_value=dest_tray.barcode.value if dest_tray.barcode else None,
                 shelved_dt=sjc.shelved_dt,
                 scanned_for_shelving=sjc.scanned_for_shelving,
                 next_available_position=None, # Not applicable for item move
                 shelving_container_id=sjc.id
             )

    # ---------------------------------------------------------
    # 3. Handle Legacy Shelf Assignment (Existing Logic)
    # ---------------------------------------------------------
    # This block executes if no destination_tray_id/barcode is provided,
    # meaning it's a direct shelf assignment for Tray or NonTrayItem.
    
    # Ensure container is a Tray or NonTrayItem for shelf assignment
    if container_type not in ["Tray", "NonTrayItem"]:
        raise ValidationException(detail=f"Container type '{container_type}' cannot be assigned directly to a shelf position. Use 'destination_tray_id' for Item moves.")

    # get shelf
    shelf_id = None
    if reassignment_input.shelf_id:
        shelf_id = reassignment_input.shelf_id
    elif reassignment_input.shelf_barcode_value:
        # V2 FIX: session.exec().all() -> session.execute(select(...)).all()
        shelf_barcode_join = (
            select(Shelf, Barcode)
            .join(Barcode)
            .where(Barcode.value == reassignment_input.shelf_barcode_value)
        )
        shelf_barcode_join = session.execute(shelf_barcode_join).first() # Changed to first() as we expect one shelf
        
        if not shelf_barcode_join:
            raise NotFound(
                detail=f"No shelves were found with barcode {reassignment_input.shelf_barcode_value}"
            )
        shelf_id = shelf_barcode_join.Shelf.id
    else:
        raise ValidationException(
            detail="Either shelf_id or shelf_barcode_value must be provided for shelf assignment."
        )
    
    # get shelf position - direct query on position_number
    shelf_position = (
        session.execute(
            select(ShelfPosition)
            .where(ShelfPosition.shelf_id == shelf_id)
            .where(ShelfPosition.position_number == reassignment_input.shelf_position_number)
        )
        .scalars()
        .first()
    )

    if not shelf_position:
        raise ValidationException(
            detail=f"""Shelf Position Number {reassignment_input.shelf_position_number} does not exist on shelf {shelf_id}"""
        )

    # Check for Availability
    shelf = shelf_position.shelf

    # check if tray or non-tray
    if container_type == "Tray":
        # V2 FIX: session.query().filter().where().first() -> session.execute(select(...)).scalars().first()
        tray_exists = (
            session.execute(select(Tray)
            .filter(Tray.shelf_position_id == shelf_position.id)
            .where(Tray.id != container.id))
            .scalars()
            .first()
        )

        # V2 FIX
        non_tray_exists = (
            session.execute(select(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .filter(NonTrayItem.shelf_position_id == shelf_position.id))
            .scalars()
            .first()
        )
    else: # container_type == "NonTrayItem"
        # V2 FIX
        tray_exists = (
            session.execute(select(Tray)
            .filter(Tray.shelf_position_id == shelf_position.id))
            .scalars()
            .first()
        )

        # V2 FIX
        non_tray_exists = (
            session.execute(select(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .filter(NonTrayItem.shelf_position_id == shelf_position.id)
            .where(NonTrayItem.id != container.id))
            .scalars()
            .first()
        )
    # grab shelving job for user_id
    # V2 FIX
    shelving_job = session.execute(select(ShelvingJob).where(ShelvingJob.id == id)).scalars().first()
    shelf_type = shelf.shelf_type
    pre_assigned_location = None
    if container_type == "Tray":
        discrepancy_tray_id = container.id
        discrepancy_non_tray_id = None
    else: # container_type == "NonTrayItem"
        discrepancy_tray_id = None
        discrepancy_non_tray_id = container.id

    if container.shelf_position_proposed_id:
        # V2 FIX
        pre_assigned_location = (
            session.execute(select(ShelfPosition)
            .where(ShelfPosition.id == container.shelf_position_proposed_id))
            .scalars()
            .first()
        ).location

    # V2 FIX
    accession_job = (session.execute(select(AccessionJob)
                     .where(AccessionJob.id == container.accession_job_id)).scalars().first())
    # Legacy containers carry scanned_for_accession=True but no accession_job_id;
    # passes_job_gate trusts the scanned flag and only enforces job completion
    # when the container actually references an accession job.
    if not passes_job_gate(
        scanned=container.scanned_for_accession,
        job_id=container.accession_job_id,
        job=accession_job,
        completed_status=AccessionJobStatus.Completed,
    ):
        barcode = container.barcode

        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=discrepancy_tray_id,
            non_tray_item_id=discrepancy_non_tray_id,
            assigned_user_id=shelving_job.assigned_user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf.location,
            pre_assigned_location=pre_assigned_location,
            error=f"""Not Accessioned Discrepancy - Container barcode {barcode.value} has not been accessioned""",
        )
        commit_record(session, new_shelving_job_discrepancy)
        raise ValidationException(detail=f"Container barcode {barcode.value} has not been accessioned")

    # V2 FIX
    verification_job = (
        session.execute(select(VerificationJob)
        .where(VerificationJob.id == container.verification_job_id)).scalars().first()
    )
    # Same as accession above: legacy containers have scanned_for_verification=True
    # but no verification_job_id, so only enforce job completion when one is set.
    if not passes_job_gate(
        scanned=container.scanned_for_verification,
        job_id=container.verification_job_id,
        job=verification_job,
        completed_status=VerificationJobStatus.Completed,
    ):
        barcode = container.barcode

        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=discrepancy_tray_id,
            non_tray_item_id=discrepancy_non_tray_id,
            assigned_user_id=shelving_job.assigned_user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf.location,
            pre_assigned_location=pre_assigned_location,
            error=f"""Not Accessioned Discrepancy - Container barcode {barcode.value} has not been verified""",
        )
        commit_record(session, new_shelving_job_discrepancy)
        raise ValidationException(
            detail=f"Container barcode {barcode.value} has not been verified"
            )

    if shelf.available_space <= 0:
        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=discrepancy_tray_id,
            non_tray_item_id=discrepancy_non_tray_id,
            assigned_user_id=shelving_job.assigned_user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf.location,
            pre_assigned_location=pre_assigned_location,
            error=f"""Available Space Discrepancy - Shelf location {shelf.location}
                    has no available space""",
        )
        commit_record(session, new_shelving_job_discrepancy)
        raise ValidationException(detail=f"Shelf ID {shelf.id} has no available space")

    if tray_exists or non_tray_exists:
        shelf_position_location = (
            shelf.location + "-" + str(reassignment_input.shelf_position_number)
        )
        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=discrepancy_tray_id,
            non_tray_item_id=discrepancy_non_tray_id,
            assigned_user_id=shelving_job.assigned_user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf_position.location,
            pre_assigned_location=pre_assigned_location,
            error=f"""Shelf Position Discrepancy - Shelf Position {shelf_position_location}
                    is already occupied""",
        )
        commit_record(session, new_shelving_job_discrepancy)
        raise ValidationException(
            detail=f"""Shelf Position {shelf_position_location} is already occupied"""
        )

    # Check if the container owner and size class match to shelf
    # Allow auto-assignment if shelf has "Unassigned" values
    # Also allow child owner items on parent owner shelves if setting is enabled
    shelf_owner = session.get(Owner, shelf.owner_id)
    shelf_size_class = session.get(SizeClass, shelf_type.size_class_id)
    
    owner_mismatch = container.owner_id != shelf.owner_id
    size_class_mismatch = container.size_class_id != shelf_type.size_class_id
    
    # Check if hierarchical owner shelving is allowed
    allow_child_owner_shelving = get_setting_value(session, "allow_child_owner_shelving", "false") == "true"
    is_child_of_shelf_owner = (
        owner_mismatch and 
        allow_child_owner_shelving and 
        is_child_of_owner(session, container.owner_id, shelf.owner_id)
    )
    
    if owner_mismatch or size_class_mismatch:
        shelf_owner_unassigned = shelf_owner and shelf_owner.name == "Unassigned"
        shelf_size_class_unassigned = shelf_size_class and shelf_size_class.name == "Unassigned"
        
        can_auto_assign = (
            (not owner_mismatch or shelf_owner_unassigned or is_child_of_shelf_owner) and
            (not size_class_mismatch or shelf_size_class_unassigned)
        )
        
        if can_auto_assign:
            # Auto-assign owner from container (only if shelf is Unassigned, NOT for hierarchical)
            if owner_mismatch and shelf_owner_unassigned:
                shelf.owner_id = container.owner_id
                session.add(shelf)
            # Note: If is_child_of_shelf_owner, shelf.owner_id stays as parent (no update)
            
            # Auto-assign shelf_type by finding existing ShelfType with matching size_class
            if size_class_mismatch and shelf_size_class_unassigned:
                # Get old capacity before changing shelf_type
                old_shelf_type = session.get(ShelfType, shelf.shelf_type_id)
                old_capacity = old_shelf_type.max_capacity if old_shelf_type else 0
                
                matching_shelf_type = session.execute(
                    select(ShelfType).where(ShelfType.size_class_id == container.size_class_id)
                ).scalars().first()
                
                if not matching_shelf_type:
                    raise ValidationException(
                        detail=f"No ShelfType exists for size class {container.size_class_id}. "
                               "Item cannot be shelved."
                    )
                
                new_capacity = matching_shelf_type.max_capacity
                
                # Update shelf_type
                shelf.shelf_type_id = matching_shelf_type.id
                session.add(shelf)
                
                # Create shelf positions for the new capacity
                if new_capacity > old_capacity:
                    new_position_numbers_range = list(range(old_capacity + 1, new_capacity + 1))
                    
                    for position_num in new_position_numbers_range:
                        new_position = ShelfPosition(
                            shelf_id=shelf.id,
                            position_number=position_num,
                        )
                        session.add(new_position)
                    
                    session.flush()  # Ensure positions are created before recalculating
                
                # Recalculate available space
                if hasattr(shelf, 'calc_available_space'):
                    shelf.calc_available_space(session=session)
                    session.add(shelf)
                
                # Update shelf_type reference for subsequent logic
                shelf_type = matching_shelf_type
        else:
            # Create a Discrepancy
            discrepancy_error = "Unknown"
            if container_type == "Tray":
                discrepancy_tray_id = container.id
                discrepancy_non_tray_id = None
            else: # container_type == "NonTrayItem"
                discrepancy_tray_id = None
                discrepancy_non_tray_id = container.id
            if container.size_class_id != shelf_type.size_class_id:
                discrepancy_error = f"""Size Discrepancy - Container size_id: {container.size_class_id} does not match Shelf size_id: {shelf_type.size_class_id}"""
            if container.owner_id != shelf.owner_id:
                discrepancy_error = f"""Owner Discrepancy does not match Container owner_id: {container.owner_id} does not match Shelf owner_id: {shelf.owner_id}"""

            new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
                shelving_job_id=id,
                tray_id=discrepancy_tray_id,
                non_tray_item_id=discrepancy_non_tray_id,
                assigned_user_id=shelving_job.assigned_user_id,
                owner_id=shelf.owner_id,
                size_class_id=shelf_type.size_class_id,
                assigned_location=shelf_position.location,
                pre_assigned_location=pre_assigned_location,
                error=f"{discrepancy_error}",
            )
            commit_record(session, new_shelving_job_discrepancy)

            raise ValidationException(
                detail=f"Container Barcode {reassignment_input.container_barcode_value} "
                       "does not match Shelf owner and size class."
            )

    # Checking and verifying Verification Job
    if container.verification_job_id:
        verification_job = session.get(VerificationJob, container.verification_job_id)

        if verification_job.shelving_job_id is None:
            verification_job.shelving_job_id = id
            session.add(verification_job)
            session.commit()
            session.refresh(verification_job)

    # only reassign actual, not proposed
    container.shelving_job_id = id
    old_shelf_position_id = container.shelf_position_id
    container.shelf_position_id = shelf_position.id

    if reassignment_input.shelved_dt is not None:
        container.shelved_dt = reassignment_input.shelved_dt

    # bool value, explicitly check if user sent value
    if reassignment_input.scanned_for_shelving is not None:
        container.scanned_for_shelving = reassignment_input.scanned_for_shelving

    session.add(container)
    start_session_with_audit_info(audit_info, session)
    if container.container_type_id == 1:
        update_shelf_space_after_tray(
            session, container, container.shelf_position_id, old_shelf_position_id
        )
    else:
        update_shelf_space_after_non_tray(
            session, container, container.shelf_position_id, old_shelf_position_id
        )
    session.commit()
    session.refresh(container)

    # Create ShelvingJobContainer record for unified container tracking
    shelving_container = _create_or_get_shelving_container(
        session=session,
        shelving_job_id=id,
        tray=container if container.container_type_id == 1 else None,
        non_tray_item=container if container.container_type_id != 1 else None,
        shelf_position=shelf_position,
        status="Shelved"
    )
    session.commit()
    session.refresh(shelving_container)

    # Log shelving audit event
    barcode_obj = session.get(Barcode, container.barcode_id) if hasattr(container, 'barcode_id') else None
    barcode_val = barcode_obj.value if barcode_obj else str(container.id)
    log_audit_event(
        session,
        AuditEventType.CONTAINER_SHELVED,
        f"{barcode_val} shelved at position {shelf_position.position_number} on shelf {shelf.barcode.value if shelf.barcode else shelf.id}",
        job_type="shelving_jobs",
        job_id=id,
        entity_type="trays" if container_type == "Tray" else "non_tray_items",
        entity_id=container.id,
    )
    session.commit()

    # Calculate next available position for frontend auto-suggest
    from app.routers.shelves import get_next_available_position
    
    direction = get_setting_value(session, "shelf_position_auto_assign_direction", "low_to_high")
    next_position = get_next_available_position(session, shelf.id, direction)
    
    # Add next_available_position and shelving_container_id to the response
    container.next_available_position = next_position
    container.shelving_container_id = shelving_container.id

    return container


@router.post(
    "/{id}/reassign-proposed-location",
    response_model=ReAssignmentOutput,
    dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))]
)
def reassign_container_proposed_location(
    id: int,
    reassignment_input: ProposedReAssignmentInput,
    session: Session = Depends(get_session),
):
    shelving_job = session.get(ShelvingJob, id)
    shelf_id = None

    if reassignment_input.shelf_id:
        shelf_id = reassignment_input.shelf_id
    elif reassignment_input.shelf_barcode_value:
        # V2 FIX: session.exec().first() -> session.execute(select(...)).scalars().first()
        existing_shelf = (
            session.execute(select(Shelf)
            .join(Barcode)
            .where(Barcode.value == reassignment_input.shelf_barcode_value))
            .scalars()
            .first()
        )

        if not existing_shelf:
            raise NotFound(
                detail=f"No shelves were found with barcode {reassignment_input.shelf_barcode_value}"
            )
        shelf_id = existing_shelf.id

    if shelf_id is None:
        raise NotFound(
            detail=f"No shelves were found"
        )

    # get shelf position - direct query on position_number
    shelf_position = (
        session.execute(
            select(ShelfPosition)
            .where(ShelfPosition.shelf_id == shelf_id)
            .where(ShelfPosition.position_number == reassignment_input.shelf_position_number)
        )
        .scalars()
        .first()
    )

    if not shelf_position:
        raise ValidationException(
            detail=f"""Shelf Position Number {reassignment_input.shelf_position_number} does not exist on shelf"""
        )

    # Check for Availability
    shelf = shelf_position.shelf
    non_tray_container = None

    # V2 FIX
    tray_container = session.execute(
        select(Tray)
        .join(Barcode, Tray.barcode_id == Barcode.id)
        .where(Barcode.value == reassignment_input.container_barcode_value)
    ).scalars().first()
    if not tray_container:
        # V2 FIX
        non_tray_container = session.execute(
            select(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .where(Barcode.value == reassignment_input.container_barcode_value)
        ).scalars().first()
        if not non_tray_container:
            raise NotFound(
                detail=f"No containers were found with barcode {reassignment_input.container_barcode_value}"
            )
        container = non_tray_container
        # Checking if position is already occupied by another container
        # V2 FIX
        tray_exists = (
            session.execute(select(Tray)
            .filter(Tray.shelf_position_id == shelf_position.id))
            .scalars()
            .first()
        )
        # V2 FIX
        non_tray_exists = (
            session.execute(select(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .filter(NonTrayItem.shelf_position_id == shelf_position.id)
            .where(NonTrayItem.id != container.id))
            .scalars()
            .first()
        )
    else:
        container = tray_container
        # Checking if position is already occupied by another container
        # V2 FIX
        tray_exists = (
            session.execute(select(Tray)
            .filter(Tray.shelf_position_id == shelf_position.id)
            .where(Tray.id != container.id))
            .scalars()
            .first()
        )
        # V2 FIX
        non_tray_exists = (
            session.execute(select(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .filter(NonTrayItem.shelf_position_id == shelf_position.id))
            .scalars()
            .first()
        )

    shelf_type = shelf.shelf_type
    shelf_position_location = (
        shelf.location + "-" + str(reassignment_input.shelf_position_number)
    )
    # Check if position is not already occupied by another container
    if tray_exists or non_tray_exists:
        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=tray_container.id if tray_container else None,
            non_tray_item_id=non_tray_container.id if non_tray_container else None,
            assigned_user_id=shelving_job.assigned_user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf_position.location,
            pre_assigned_location=shelf_position_location,
            error=f"""Shelf Position Discrepancy - Shelf Position {shelf_position_location} is already occupied""",
        )
        commit_record(session, new_shelving_job_discrepancy)

        raise ValidationException(
            detail=f"""Shelf Position {shelf_position_location} is already occupied"""
        )

    # Checking for available_space on shelf
    if shelf.available_space <= 0:
        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=tray_container.id if tray_container else None,
            non_tray_item_id=non_tray_container.id if non_tray_container else None,
            assigned_user_id=shelving_job.assigned_user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf.location,
            pre_assigned_location=shelf_position_location,
            error=f"""Available Space Discrepancy - Shelf location {shelf.location} has no available space""",
        )
        commit_record(session, new_shelving_job_discrepancy)

        raise ValidationException(detail=f"Shelf ID {shelf.id} has no available space")

    # Check if the container owner and size class match to shelf
    # Allow auto-assignment if shelf has "Unassigned" values
    # Also allow child owner items on parent owner shelves if setting is enabled
    shelf_owner = session.get(Owner, shelf.owner_id)
    shelf_size_class = session.get(SizeClass, shelf_type.size_class_id)
    
    owner_mismatch = container.owner_id != shelf.owner_id
    size_class_mismatch = container.size_class_id != shelf_type.size_class_id
    
    # Check if hierarchical owner shelving is allowed
    allow_child_owner_shelving = get_setting_value(session, "allow_child_owner_shelving", "false") == "true"
    is_child_of_shelf_owner = (
        owner_mismatch and 
        allow_child_owner_shelving and 
        is_child_of_owner(session, container.owner_id, shelf.owner_id)
    )
    
    if owner_mismatch or size_class_mismatch:
        shelf_owner_unassigned = shelf_owner and shelf_owner.name == "Unassigned"
        shelf_size_class_unassigned = shelf_size_class and shelf_size_class.name == "Unassigned"
        
        can_auto_assign = (
            (not owner_mismatch or shelf_owner_unassigned or is_child_of_shelf_owner) and
            (not size_class_mismatch or shelf_size_class_unassigned)
        )
        
        if can_auto_assign:
            # Auto-assign owner from container (only if shelf is Unassigned, NOT for hierarchical)
            if owner_mismatch and shelf_owner_unassigned:
                shelf.owner_id = container.owner_id
                session.add(shelf)
            # Note: If is_child_of_shelf_owner, shelf.owner_id stays as parent (no update)
            
            # Auto-assign shelf_type by finding existing ShelfType with matching size_class
            if size_class_mismatch and shelf_size_class_unassigned:
                # Get old capacity before changing shelf_type
                old_shelf_type = session.get(ShelfType, shelf.shelf_type_id)
                old_capacity = old_shelf_type.max_capacity if old_shelf_type else 0
                
                matching_shelf_type = session.execute(
                    select(ShelfType).where(ShelfType.size_class_id == container.size_class_id)
                ).scalars().first()
                
                if not matching_shelf_type:
                    raise ValidationException(
                        detail=f"No ShelfType exists for size class {container.size_class_id}. "
                               "Item cannot be shelved."
                    )
                
                new_capacity = matching_shelf_type.max_capacity
                
                # Update shelf_type
                shelf.shelf_type_id = matching_shelf_type.id
                session.add(shelf)
                
                # Create shelf positions for the new capacity
                if new_capacity > old_capacity:
                    new_position_numbers_range = list(range(old_capacity + 1, new_capacity + 1))
                    
                    for position_num in new_position_numbers_range:
                        new_position = ShelfPosition(
                            shelf_id=shelf.id,
                            position_number=position_num,
                        )
                        session.add(new_position)
                    
                    session.flush()  # Ensure positions are created before recalculating
                
                # Recalculate available space
                if hasattr(shelf, 'calc_available_space'):
                    shelf.calc_available_space(session=session)
                    session.add(shelf)
                
                # Update shelf_type reference for subsequent logic
                shelf_type = matching_shelf_type
        else:
            # Create a Discrepancy
            discrepancy_error = "Unknown"
            if container.container_type_id == 1:
                discrepancy_tray_id = container.id
                discrepancy_non_tray_id = None
            else:
                discrepancy_tray_id = None
                discrepancy_non_tray_id = container.id
            if container.size_class_id != shelf_type.size_class_id:
                discrepancy_error = f"""Size Discrepancy - Container size_id: {container.size_class_id} does not match Shelf size_id: {shelf_type.size_class_id}"""
            if container.owner_id != shelf.owner_id:
                discrepancy_error = f"""Owner Discrepancy does not match Container owner_id: {container.owner_id} does not match Shelf owner_id: {shelf.owner_id}"""

            new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
                shelving_job_id=id,
                tray_id=discrepancy_tray_id,
                non_tray_item_id=discrepancy_non_tray_id,
                assigned_user_id=shelving_job.assigned_user_id,
                owner_id=shelf.owner_id,
                size_class_id=shelf_type.size_class_id,
                assigned_location=shelf_position.location,
                pre_assigned_location=shelf_position_location,
                error=f"{discrepancy_error}",
            )
            commit_record(session, new_shelving_job_discrepancy)

            raise ValidationException(
                detail=f"Container Barcode {reassignment_input.container_barcode_value} does not match Shelf owner and size class."
            )

    setattr(
        container, "shelf_position_proposed_id",
        shelf_position.id
    )
    setattr(container, "update_dt", datetime.now(timezone.utc))

    # Checking container has already been shelved and shelving_job not Completed,
    # need to update the container shelf_position_id as well.
    if (
        container.shelf_position_id is not None and
        container.shelf_position_id != shelf_position.id and
        shelving_job.status != "Completed"
    ):
        old_shelf_position_id = container.shelf_position_id
        setattr(
            container, "shelf_position_id",
            shelf_position.id
        )
        if container.container_type_id == 1:
            update_shelf_space_after_tray(
                session, container, container.shelf_position_id, old_shelf_position_id
            )
        else:
            update_shelf_space_after_non_tray(
                session, container, container.shelf_position_id, old_shelf_position_id
            )

    session.add(container)
    session.commit()
    session.refresh(container)
    session.refresh(shelving_job)

    setattr(container, "shelf_position", shelf_position)
    return container


# ==============================================================================
# SHELVE BY LIST ENDPOINTS
# ==============================================================================

from app.models.shelving_jobs import ShelvingMode, OriginStatus
from app.models.shelving_job_containers import ShelvingJobContainer, ShelvingJobContainerStatus
from app.schemas.shelving_job_containers import (
    ShelveByListJobInput,
    ShelvingJobContainerInput,
    ShelvingJobContainerOutput,
    ShelvingJobContainerOverrideInput,
    PreAssignmentInput,
    PreAssignmentResult as PreAssignmentResultSchema,
    OfflineShelveConfirmation,
)
from app.services.shelving_assignment import shelving_assignment_service


@router.post("/list", response_model=ShelvingJobDetailOutput, status_code=201, deprecated=True, dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))])
def create_shelve_by_list_job(
    job_input: ShelveByListJobInput,
    session: Session = Depends(get_session),
):
    """
    DEPRECATED: Use POST /shelving-jobs/ with origin='List' instead.
    
    Create a new Shelve by List job.
    This endpoint is maintained for backward compatibility.
    """
    # Convert ShelveByListJobInput to unified ShelvingJobInput
    unified_input = ShelvingJobInput(
        origin="List",
        mode=job_input.mode,
        building_id=job_input.building_id,
        created_by_id=job_input.created_by_id,
        verification_job_ids=job_input.verification_job_ids,
        allow_unassigned_size=job_input.allow_unassigned_size,
        allow_unassigned_owner=job_input.allow_unassigned_owner,
        allow_tiered_owner=job_input.allow_tiered_owner,
    )
    # Delegate to unified endpoint
    return create_shelving_job(unified_input, session)


@router.post("/{id}/cancel", dependencies=[Depends(RequiresPermission("delete_shelving_jobs"))])
def cancel_shelve_by_list_job(
    id: int,
    session: Session = Depends(get_session),
):
    """
    Cancel a Shelve by List job (only if status is 'Created').
    
    This deletes all containers from the job, freeing them to be added
    to another job, and sets the job status to 'Cancelled'.
    """
    shelving_job = session.get(ShelvingJob, id)
    if not shelving_job:
        raise NotFound(detail=f"Shelving Job ID {id} Not Found")
    
    if shelving_job.origin != "List":
        raise ValidationException(detail="Only Shelve by List jobs can be cancelled this way")
    
    if shelving_job.status != ShelvingJobStatus.Created:
        raise ValidationException(
            detail=f"Cannot cancel job with status '{shelving_job.status}'. "
                   f"Only jobs with status 'Created' can be cancelled."
        )
    
    # Delete all containers from this job
    containers = session.execute(
        select(ShelvingJobContainer).where(ShelvingJobContainer.shelving_job_id == id)
    ).scalars().all()
    
    for container in containers:
        session.delete(container)
    
    # Update job status to Cancelled
    shelving_job.status = "Cancelled"
    session.add(shelving_job)
    session.commit()
    
    return {"message": f"Job {id} cancelled. {len(containers)} containers released."}


@router.get("/{id}/containers", response_model=List[ShelvingJobContainerOutput], dependencies=[Depends(RequiresPermission("can_access_shelving"))])
def get_shelving_job_containers(
    id: int,
    status: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """
    Get all containers in a Shelve by List job.
    
    Optional filter by status: Pending, Assigned, Unassigned, Shelved, Error
    """
    shelving_job = session.get(ShelvingJob, id)
    if not shelving_job:
        raise NotFound(detail=f"Shelving Job ID {id} Not Found")
    
    query = select(ShelvingJobContainer).where(
        ShelvingJobContainer.shelving_job_id == id
    )
    
    if status:
        query = query.where(ShelvingJobContainer.status == status)
    
    containers = session.execute(query).scalars().all()
    
    # Enrich with container details
    result = []
    for container in containers:
        output = _build_container_output(session, container)
        result.append(output)
    
    return result


@router.post("/{id}/containers", response_model=ShelvingJobContainerOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))])
def add_container_to_shelving_job(
    id: int,
    container_input: ShelvingJobContainerInput,
    session: Session = Depends(get_session),
):
    """
    Add a container (tray or non-tray item) to a Shelve by List job.
    
    Validates:
    - Container exists and is on a completed verification job
    - Container is not already shelved
    - Container is not on another active shelving job
    """
    shelving_job = session.get(ShelvingJob, id)
    if not shelving_job:
        raise NotFound(detail=f"Shelving Job ID {id} Not Found")
    
    if shelving_job.origin != OriginStatus.List:
        raise ValidationException(detail="Can only add containers to Shelve by List jobs")
    
    if shelving_job.status not in [ShelvingJobStatus.Created, ShelvingJobStatus.Paused]:
        raise ValidationException(detail="Cannot add containers to a running or completed job")
    
    # Validate the container
    result = shelving_assignment_service.validate_container_for_list(
        session, container_input.container_barcode, id
    )
    
    if not result.is_valid:
        raise ValidationException(detail=result.error_message)
    
    # Check if already in this job's list
    existing_query = select(ShelvingJobContainer).where(
        ShelvingJobContainer.shelving_job_id == id
    )
    if result.container_type == "Tray":
        existing_query = existing_query.where(
            ShelvingJobContainer.tray_id == result.container_id
        )
    else:
        existing_query = existing_query.where(
            ShelvingJobContainer.non_tray_item_id == result.container_id
        )
    
    existing = session.execute(existing_query).scalars().first()
    if existing:
        raise ValidationException(
            detail=f"Container {container_input.container_barcode} is already in this job's list"
        )
    
    # Create the container entry
    new_container = ShelvingJobContainer(
        shelving_job_id=id,
        tray_id=result.container_id if result.container_type == "Tray" else None,
        non_tray_item_id=result.container_id if result.container_type == "NonTray" else None,
        status=ShelvingJobContainerStatus.PENDING
    )
    session.add(new_container)
    session.commit()
    session.refresh(new_container)

    log_audit_event(
        session,
        AuditEventType.ITEM_ADDED,
        f"Container {container_input.container_barcode} added to Shelving Job {id}",
        job_type="shelving_jobs",
        job_id=id,
    )
    session.commit()

    return _build_container_output(session, new_container)


@router.delete("/{id}/containers/{container_id}", status_code=204, dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))])
def remove_container_from_shelving_job(
    id: int,
    container_id: int,
    session: Session = Depends(get_session),
):
    """
    Remove a container from a Shelve by List job.
    """
    shelving_job = session.get(ShelvingJob, id)
    if not shelving_job:
        raise NotFound(detail=f"Shelving Job ID {id} Not Found")
    
    container = session.get(ShelvingJobContainer, container_id)
    if not container or container.shelving_job_id != id:
        raise NotFound(detail=f"Container ID {container_id} not found in job {id}")
    
    if container.status == ShelvingJobContainerStatus.SHELVED:
        raise ValidationException(detail="Cannot remove a container that has already been shelved")
    
    container_barcode_value = str(container_id)
    if container.tray:
        container_barcode_value = container.tray.barcode.value if container.tray.barcode else f"Tray {container.tray.id}"
    elif container.non_tray_item:
        container_barcode_value = container.non_tray_item.barcode.value if container.non_tray_item.barcode else f"NTI {container.non_tray_item.id}"

    log_audit_event(
        session,
        AuditEventType.ITEM_REMOVED,
        f"Container {container_barcode_value} removed from Shelving Job {id}",
        job_type="shelving_jobs",
        job_id=id,
    )
    session.delete(container)
    session.commit()
    return None


@router.post("/{id}/pre-assign", response_model=PreAssignmentResultSchema, dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))])
def pre_assign_shelving_job(
    id: int,
    pre_assign_input: PreAssignmentInput,
    session: Session = Depends(get_session),
):
    """
    Run pre-assignment algorithm to assign shelf positions to containers.
    
    Validates physical dimensions (shelf height >= container size class height).
    Supports partial assignment - containers that can't be assigned are marked as 'Unassigned'.
    """
    shelving_job = session.get(ShelvingJob, id)
    if not shelving_job:
        raise NotFound(detail=f"Shelving Job ID {id} Not Found")
    
    if shelving_job.origin != OriginStatus.List:
        raise ValidationException(detail="Pre-assignment only available for Shelve by List jobs")
    
    if shelving_job.status not in [ShelvingJobStatus.Created, ShelvingJobStatus.Paused]:
        raise ValidationException(detail="Cannot pre-assign a running or completed job")
    
    result = shelving_assignment_service.pre_assign_containers(
        session=session,
        shelving_job_id=id,
        building_id=pre_assign_input.building_id,
        module_id=pre_assign_input.module_id,
        aisle_id=pre_assign_input.aisle_id,
        ladder_id=pre_assign_input.ladder_id,
        allow_unassigned_size=shelving_job.allow_unassigned_size,
        allow_unassigned_owner=shelving_job.allow_unassigned_owner,
        allow_tiered_owner=shelving_job.allow_tiered_owner
    )
    
    return PreAssignmentResultSchema(
        assigned_count=result.assigned_count,
        unassigned_count=result.unassigned_count,
        unassigned_barcodes=result.unassigned_barcodes,
        message=result.message
    )


@router.patch("/{id}/containers/{container_id}/override", response_model=ShelvingJobContainerOutput, dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))])
def override_container_location(
    id: int,
    container_id: int,
    override_input: ShelvingJobContainerOverrideInput,
    session: Session = Depends(get_session),
):
    """
    Override the proposed shelf location for a container.
    
    Can be used before or during job execution.
    """
    shelving_job = session.get(ShelvingJob, id)
    if not shelving_job:
        raise NotFound(detail=f"Shelving Job ID {id} Not Found")
    
    container = session.get(ShelvingJobContainer, container_id)
    if not container or container.shelving_job_id != id:
        raise NotFound(detail=f"Container ID {container_id} not found in job {id}")
    
    if container.status == ShelvingJobContainerStatus.SHELVED:
        raise ValidationException(detail="Cannot override location for already shelved container")
    
    # Find the shelf position
    shelf_position = None
    if override_input.shelf_position_id:
        shelf_position = session.get(ShelfPosition, override_input.shelf_position_id)
    elif override_input.shelf_barcode:
        barcode = session.execute(
            select(Barcode).where(Barcode.value == override_input.shelf_barcode)
        ).scalars().first()
        if barcode:
            shelf = session.execute(
                select(Shelf).where(Shelf.barcode_id == barcode.id)
            ).scalars().first()
            if shelf and override_input.shelf_position_number:
                shelf_position = session.execute(
                    select(ShelfPosition)
                    .where(ShelfPosition.shelf_id == shelf.id)
                    .where(ShelfPosition.position_number == override_input.shelf_position_number)
                ).scalars().first()
    
    if not shelf_position:
        raise NotFound(detail="Shelf position not found")
    
    # Update the container
    container.proposed_shelf_position_id = shelf_position.id
    container.position_reserved_at = datetime.now(timezone.utc)
    container.status = ShelvingJobContainerStatus.ASSIGNED
    container.was_overridden = True
    container.override_reason = override_input.reason or "User Override"
    
    session.add(container)
    session.commit()
    session.refresh(container)
    
    return _build_container_output(session, container)


@router.post("/{id}/scan-container", dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))])
def scan_container_for_shelving(
    id: int,
    container_barcode: str,
    session: Session = Depends(get_session),
):
    """
    Scan a container barcode during job execution.
    
    Returns the proposed location for pre-assigned mode,
    or validates the container is on the list for manual mode.
    """
    shelving_job = session.get(ShelvingJob, id)
    if not shelving_job:
        raise NotFound(detail=f"Shelving Job ID {id} Not Found")
    
    # Find the container in the job's list
    barcode = session.execute(
        select(Barcode).where(Barcode.value == container_barcode)
    ).scalars().first()
    
    if not barcode:
        raise NotFound(detail=f"Barcode {container_barcode} not found")
    
    # Check trays
    tray = session.execute(
        select(Tray).where(Tray.barcode_id == barcode.id)
    ).scalars().first()
    
    container_entry = None
    if tray:
        container_entry = session.execute(
            select(ShelvingJobContainer)
            .where(ShelvingJobContainer.shelving_job_id == id)
            .where(ShelvingJobContainer.tray_id == tray.id)
        ).scalars().first()
    
    if not container_entry:
        # Check non-tray items
        non_tray = session.execute(
            select(NonTrayItem).where(NonTrayItem.barcode_id == barcode.id)
        ).scalars().first()
        if non_tray:
            container_entry = session.execute(
                select(ShelvingJobContainer)
                .where(ShelvingJobContainer.shelving_job_id == id)
                .where(ShelvingJobContainer.non_tray_item_id == non_tray.id)
            ).scalars().first()
    
    if not container_entry:
        raise ValidationException(
            detail=f"Container {container_barcode} is not on this job's list"
        )
    
    if container_entry.status == ShelvingJobContainerStatus.SHELVED:
        raise ValidationException(
            detail=f"Container {container_barcode} has already been shelved"
        )
    
    return _build_container_output(session, container_entry)


@router.post("/{id}/confirm-shelve", response_model=ShelvingJobContainerOutput, dependencies=[Depends(RequiresPermission("can_create_and_execute_shelving_job"))])
def confirm_container_shelved(
    id: int,
    confirmation: OfflineShelveConfirmation,
    session: Session = Depends(get_session),
):
    """
    Confirm that a container has been shelved at a location.
    
    For pre-assigned mode: validates the shelf barcode matches proposed location.
    If wrong shelf is scanned, returns an error.
    For manual mode: records the shelving action.
    Supports offline sync by accepting timestamp.
    """
    shelving_job = session.get(ShelvingJob, id)
    if not shelving_job:
        raise NotFound(detail=f"Shelving Job ID {id} Not Found")
    
    container = session.get(ShelvingJobContainer, confirmation.container_id)
    if not container or container.shelving_job_id != id:
        raise NotFound(detail=f"Container ID {confirmation.container_id} not found in job {id}")
    
    # Determine the shelf position
    shelf_position = None
    scanned_shelf_barcode = confirmation.shelf_barcode
    
    if scanned_shelf_barcode:
        # Look up the shelf from barcode
        shelf_barcode = session.execute(
            select(Barcode).where(Barcode.value == scanned_shelf_barcode)
        ).scalars().first()
        
        if not shelf_barcode:
            raise ValidationException(detail=f"Shelf barcode '{scanned_shelf_barcode}' not found")
        
        # Find the shelf with this barcode
        scanned_shelf = session.execute(
            select(Shelf).where(Shelf.barcode_id == shelf_barcode.id)
        ).scalars().first()
        
        if not scanned_shelf:
            raise ValidationException(detail=f"No shelf found with barcode '{scanned_shelf_barcode}'")
        
        # For pre-assigned mode, validate the shelf matches
        if container.proposed_shelf_position_id:
            proposed_position = session.get(ShelfPosition, container.proposed_shelf_position_id)
            if proposed_position:
                proposed_shelf = session.get(Shelf, proposed_position.shelf_id)
                if proposed_shelf and proposed_shelf.id != scanned_shelf.id:
                    # Wrong shelf scanned!
                    raise ValidationException(
                        detail=f"Wrong shelf scanned. Expected shelf barcode for location '{proposed_position.location}', "
                               f"but scanned '{scanned_shelf_barcode}'"
                    )
                # Use the pre-assigned position since shelf matches
                shelf_position = proposed_position
        
        # For manual mode (no pre-assignment), find an available position on the shelf
        if not shelf_position:
            # Get all positions on this shelf
            all_positions = session.execute(
                select(ShelfPosition).where(ShelfPosition.shelf_id == scanned_shelf.id)
            ).scalars().all()
            
            if not all_positions:
                raise ValidationException(detail=f"No positions found on shelf '{scanned_shelf_barcode}'")
            
            # Find the first available position (not occupied by a tray or non-tray item)
            for pos in all_positions:
                # Check if position is occupied by a tray
                tray_at_pos = session.execute(
                    select(Tray).where(Tray.shelf_position_id == pos.id)
                ).scalars().first()
                if tray_at_pos:
                    continue
                    
                # Check if position is occupied by a non-tray item
                nti_at_pos = session.execute(
                    select(NonTrayItem).where(NonTrayItem.shelf_position_id == pos.id)
                ).scalars().first()
                if nti_at_pos:
                    continue
                    
                # This position is available
                shelf_position = pos
                break
            
            if not shelf_position:
                raise ValidationException(detail=f"No available positions on shelf '{scanned_shelf_barcode}'")
    elif confirmation.shelf_position_id:
        shelf_position = session.get(ShelfPosition, confirmation.shelf_position_id)
        if not shelf_position:
            raise NotFound(detail=f"Shelf position ID {confirmation.shelf_position_id} not found")
    else:
        raise ValidationException(detail="Either shelf_barcode or shelf_position_id must be provided")
    
    # Check if this is an override (scanned different position than proposed)
    is_override = confirmation.override or (
        container.proposed_shelf_position_id and 
        container.proposed_shelf_position_id != shelf_position.id
    )
    
    if is_override:
        container.was_overridden = True
        container.override_reason = confirmation.override_reason or "User Override"
    
    # Update the container
    container.actual_shelf_position_id = shelf_position.id
    container.shelved_dt = confirmation.timestamp or datetime.now(timezone.utc)
    container.status = ShelvingJobContainerStatus.SHELVED
    
    session.add(container)
    
    # Also update the actual tray/non-tray item
    if container.tray_id:
        tray = session.get(Tray, container.tray_id)
        if tray:
            old_pos_id = tray.shelf_position_id
            tray.shelf_position_id = shelf_position.id
            tray.scanned_for_shelving = True
            tray.shelving_job_id = id
            tray.shelved_dt = container.shelved_dt
            session.add(tray)
            update_shelf_space_after_tray(
                session, tray, shelf_position.id, old_pos_id
            )
    elif container.non_tray_item_id:
        non_tray = session.get(NonTrayItem, container.non_tray_item_id)
        if non_tray:
            old_pos_id = non_tray.shelf_position_id
            non_tray.shelf_position_id = shelf_position.id
            non_tray.scanned_for_shelving = True
            non_tray.shelving_job_id = id
            non_tray.shelved_dt = container.shelved_dt
            session.add(non_tray)
            update_shelf_space_after_non_tray(
                session, non_tray, shelf_position.id, old_pos_id
            )
    
    session.commit()
    session.refresh(container)
    
    return _build_container_output(session, container)


def _build_container_output(session: Session, container: ShelvingJobContainer) -> dict:
    """Build a ShelvingJobContainerOutput from a container."""
    output = {
        "id": container.id,
        "shelving_job_id": container.shelving_job_id,
        "tray_id": container.tray_id,
        "non_tray_item_id": container.non_tray_item_id,
        "proposed_shelf_position_id": container.proposed_shelf_position_id,
        "position_reserved_at": container.position_reserved_at,
        "actual_shelf_position_id": container.actual_shelf_position_id,
        "shelved_dt": container.shelved_dt,
        "was_overridden": container.was_overridden,
        "override_reason": container.override_reason,
        "status": container.status,
        "error_message": container.error_message,
        "create_dt": container.create_dt,
        "update_dt": container.update_dt,
    }
    
    # Get container details
    if container.tray_id:
        tray = session.get(Tray, container.tray_id)
        if tray:
            output["container_type"] = "Tray"
            if tray.barcode:
                output["barcode"] = {
                    "id": str(tray.barcode.id),
                    "value": tray.barcode.value,
                    "type_id": tray.barcode.type_id
                }
            if tray.owner:
                output["owner"] = {"id": tray.owner.id, "name": tray.owner.name}
            if tray.size_class:
                output["size_class"] = {
                    "id": tray.size_class.id,
                    "name": tray.size_class.name,
                    "short_name": tray.size_class.short_name
                }
    elif container.non_tray_item_id:
        non_tray = session.get(NonTrayItem, container.non_tray_item_id)
        if non_tray:
            output["container_type"] = "Non-Tray"
            if non_tray.barcode:
                output["barcode"] = {
                    "id": str(non_tray.barcode.id),
                    "value": non_tray.barcode.value,
                    "type_id": non_tray.barcode.type_id
                }
            if non_tray.owner:
                output["owner"] = {"id": non_tray.owner.id, "name": non_tray.owner.name}
            if non_tray.size_class:
                output["size_class"] = {
                    "id": non_tray.size_class.id,
                    "name": non_tray.size_class.name,
                    "short_name": non_tray.size_class.short_name
                }
    
    # Get proposed location
    if container.proposed_shelf_position_id:
        position = session.get(ShelfPosition, container.proposed_shelf_position_id)
        if position:
            output["proposed_location"] = position.location
    
    # Get actual location
    if container.actual_shelf_position_id:
        position = session.get(ShelfPosition, container.actual_shelf_position_id)
        if position:
            output["actual_location"] = position.location
    
    return output
