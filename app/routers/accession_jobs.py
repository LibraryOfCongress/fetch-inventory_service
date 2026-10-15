# /code/app/routers/accession_jobs.py - FINAL CHECKED V2

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate 
from sqlalchemy.orm import Session, selectinload 
from sqlalchemy import select, not_, or_, func, text, update 
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.filter_params import SortParams, JobFilterParams
from app.models.accession_jobs import AccessionJob
from app.models.barcodes import Barcode
from app.models.users import User
from app.models.verification_jobs import VerificationJob
from app.models.container_types import ContainerType
from app.models.workflows import Workflow
from app.sorting import BaseSorter
from app.tasks import complete_accession_job, manage_accession_job_transition
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

from app.schemas.accession_jobs import (
    AccessionJobInput,
    AccessionJobUpdateInput,
    AccessionJobListOutput,
    AccessionJobDetailOutput,
)
from app.utilities import start_session_with_audit_info
from app.services.audit_service import log_audit_event, AuditEventType

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.utils.job_assignment import auto_assign_on_start, update_status_on_assignment

router = APIRouter(
    prefix="/accession-jobs",
    tags=["accession jobs"],
    dependencies=[Depends(RequiresPermission("can_access_accession"))],
)


@router.get("/", response_model=Page[AccessionJobListOutput])
def get_accession_job_list(
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of accession jobs.
    """
    try:
        # Without these the AccessionJobListOutput.tray_count / .item_count
        # hybrid properties fall through to `len(self.trays)` etc. at
        # serialization time, which lazy-loads three relationships per row
        # (~150 queries per 50-row page). With selectinload, that collapses
        # to 3 IN-clause queries.
        query = select(AccessionJob).options(
            selectinload(AccessionJob.assigned_user),
            selectinload(AccessionJob.created_by),
            selectinload(AccessionJob.trays),
            selectinload(AccessionJob.items),
            selectinload(AccessionJob.non_tray_items),
        )

        if params.queue:
            subquery = (
                select(VerificationJob.accession_job_id)
                .where(VerificationJob.status != "Created")
                .distinct()
            )

            query = query.where(
                or_(
                    AccessionJob.id.not_in(subquery),
                    not_(subquery.exists()),
                )
            )
        if params.status and len(list(filter(None, params.status))) > 0:
            query = query.where(AccessionJob.status.in_(params.status))
        if params.workflow_id:
            query = query.where(AccessionJob.workflow_id == params.workflow_id)
        if params.assigned_user_id:
            query = query.where(AccessionJob.assigned_user_id == params.assigned_user_id)
        if params.assigned_user:
            assigned_user_subquery = (
                select(User.id)
                .where(
                    func.concat(User.first_name, ' ', User.last_name).in_(
                        params.assigned_user
                        )
                    )
                .distinct()
            )
            query = query.where(AccessionJob.assigned_user_id.in_(assigned_user_subquery))
        if params.container_type:
            subquery = (
                select(ContainerType.id)
                .where(ContainerType.type == params.container_type)
                .distinct()
            )
            query = query.where(AccessionJob.container_type_id == subquery.scalar_subquery())
        if params.trayed is not None:
            query = query.where(AccessionJob.trayed == params.trayed)
        if params.created_by_id:
            query = query.where(AccessionJob.created_by_id == params.created_by_id)
        if params.from_dt:
            query = query.where(AccessionJob.create_dt >= params.from_dt)
        if params.to_dt:
            query = query.where(AccessionJob.create_dt <= params.to_dt)

        if sort_params.sort_by:
            sorter = BaseSorter(AccessionJob)
            query = sorter.apply_sorting(query, sort_params)

        return paginate(session, query)
    except IntegrityError as e:
        raise InternalServerError(detail=f"{e}")


@router.get("/{id}", response_model=AccessionJobDetailOutput)
def get_accession_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the accession job detail for the given ID.
    """
    accession_job = session.get(AccessionJob, id)

    if accession_job:
        return accession_job

    raise NotFound(detail=f"Accession Job ID {id} Not Found")


@router.get("/workflow/{id}", response_model=AccessionJobDetailOutput)
def get_accession_job_detail_by_workflow(
    id: int, session: Session = Depends(get_session)
):
    """
    Retrieves the accession job detail for the given workflow id.
    """
    # V2 FIX
    accession_job = session.execute(
        select(AccessionJob).where(AccessionJob.workflow_id == id)
    ).scalars().first()

    if accession_job:
        return accession_job

    raise NotFound(detail=f"Accession Job ID {id} Not Found")


@router.post("/", response_model=AccessionJobDetailOutput, status_code=201,
             dependencies=[Depends(RequiresPermission("can_access_accession"))])
def create_accession_job(
    accession_job_input: AccessionJobInput, session: Session = Depends(get_session)
) -> AccessionJob:
    """
    Create a new accession job:
    """
    try:
        new_accession_job = AccessionJob(**accession_job_input.model_dump())
        
        # V2 FIX
        if new_accession_job.trayed:
            container_type = (
                session.execute(select(ContainerType).filter(ContainerType.type == "Tray"))
                .scalars()
                .first()
            )
        else:
            container_type = (
                session.execute(select(ContainerType).filter(ContainerType.type == "Non-Tray"))
                .scalars()
                .first()
            )
        new_accession_job.container_type_id = container_type.id

        workflow = Workflow()
        audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
        session.add(workflow)
        session.commit()
        session.refresh(workflow)
        new_accession_job.workflow_id = workflow.id
        session.add(new_accession_job)
        start_session_with_audit_info(audit_info, session)
        session.commit()
        session.refresh(new_accession_job)

        log_audit_event(
            session,
            AuditEventType.JOB_CREATED,
            f"Accession Job {new_accession_job.id} created",
            job_type="accession_jobs",
            job_id=new_accession_job.id,
        )
        session.commit()

        return new_accession_job

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=AccessionJobDetailOutput)
def update_accession_job(
    id: int,
    accession_job: AccessionJobUpdateInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Update an existing accession job with the provided data.
    
    Includes auto-assignment logic:
    - When a user starts a job (status → Running), auto-assign to them if unassigned
    - Prevent users from starting jobs assigned to others
    - When manager assigns a user, auto-update status to Assigned
    """
    existing_accession_job = session.get(AccessionJob, id)

    if not existing_accession_job:
        raise NotFound(detail=f"Accession Job ID {id} Not Found")

    original_status = existing_accession_job.status
    original_assigned_user_id = existing_accession_job.assigned_user_id
    mutated_data = accession_job.model_dump(exclude_unset=True)
    
    # Handle auto-assignment when user starts job
    new_status = mutated_data.get("status")
    if new_status:
        auto_assign_on_start(
            existing_accession_job, 
            new_status, 
            current_user.id
        )
    
    # Handle status update when manager assigns user
    new_assigned_user_id = mutated_data.get("assigned_user_id")
    if new_assigned_user_id is not None and "status" not in mutated_data:
        update_status_on_assignment(
            existing_accession_job,
            new_assigned_user_id,
            original_status
        )

    for key, value in mutated_data.items():
        setattr(existing_accession_job, key, value)

    setattr(existing_accession_job, "update_dt", datetime.now(timezone.utc))
    
    # V2 FIX
    if existing_accession_job.trayed:
        container_type = (
            session.execute(select(ContainerType).filter(ContainerType.type == "Tray"))
            .scalars()
            .first()
        )
    else:
        container_type = (
            session.execute(select(ContainerType).filter(ContainerType.type == "Non-Tray"))
            .scalars()
            .first()
        )
    setattr(existing_accession_job, "container_type_id", container_type.id)

    existing_accession_job = commit_record(session, existing_accession_job)

    # Log status change if status was updated
    new_status = mutated_data.get("status")
    if new_status and new_status != original_status:
        log_audit_event(
            session,
            AuditEventType.JOB_STATUS_CHANGED,
            f"Status changed from {original_status} to {new_status}",
            job_type="accession_jobs",
            job_id=id,
        )
        session.commit()

    if mutated_data.get("status") == "Completed" and original_status != "Completed":
        # V2 BATCH UPDATE FIX
        if existing_accession_job.items:
            items_barcode_ids = [
                item.barcode_id for item in existing_accession_job.items
            ]
            session.execute(
                update(Barcode)
                .where(Barcode.id.in_(items_barcode_ids), Barcode.withdrawn == True)
                .values(withdrawn=False, update_dt=datetime.now(timezone.utc))
            )

        if existing_accession_job.non_tray_items:
            non_tray_items_barcode_ids = [
                item.barcode_id for item in existing_accession_job.non_tray_items
            ]
            session.execute(
                update(Barcode)
                .where(Barcode.id.in_(non_tray_items_barcode_ids), Barcode.withdrawn == True)
                .values(withdrawn=False, update_dt=datetime.now(timezone.utc))
            )

        if existing_accession_job.trays:
            trays_barcode_ids = [
                tray.barcode_id for tray in existing_accession_job.trays
            ]
            session.execute(
                update(Barcode)
                .where(Barcode.id.in_(trays_barcode_ids), Barcode.withdrawn == True)
                .values(withdrawn=False, update_dt=datetime.now(timezone.utc))
            )

            for tray in existing_accession_job.trays:
                if tray.items:
                    items_barcode_ids = [item.barcode_id for item in tray.items]
                    session.execute(
                        update(Barcode)
                        .where(Barcode.id.in_(items_barcode_ids), Barcode.withdrawn == True)
                        .values(withdrawn=False, update_dt=datetime.now(timezone.utc))
                    )

        audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"}).copy()
        background_tasks.add_task(
            complete_accession_job,
            existing_accession_job.id, 
            original_status,
            audit_info=audit_info
        )
        session.refresh(existing_accession_job)
    else:
        audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"}).copy()
        background_tasks.add_task(
            manage_accession_job_transition,
            existing_accession_job.id,
            original_status,
            audit_info=audit_info
        )

        session.commit()
        session.refresh(existing_accession_job)

    return existing_accession_job


@router.delete("/{id}", status_code=204, dependencies=[Depends(RequiresPermission("can_cancel_accession"))])
def delete_accession_job(id: int, session: Session = Depends(get_session)):
    """
    Delete an accession job by its ID.
    """
    accession_job = session.get(AccessionJob, id)

    if accession_job:
        log_audit_event(
            session,
            AuditEventType.JOB_DELETED,
            f"Accession Job {id} deleted",
            job_type="accession_jobs",
            job_id=id,
        )
        session.delete(accession_job)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Accession Job ID {id} Not Found")