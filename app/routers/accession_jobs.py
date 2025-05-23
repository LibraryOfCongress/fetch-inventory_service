from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy import not_, or_, func, text
from sqlmodel import Session, select
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

router = APIRouter(
    prefix="/accession-jobs",
    tags=["accession jobs"],
)


@router.get("/", response_model=Page[AccessionJobListOutput])
def get_accession_job_list(
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of accession jobs.

    **Params**
    - params: The filter parameters.
        - queue: Filters out cancelled Acc Jobs and Acc Jobs where Verification has started.
        - workflow_id: The ID of the workflow.
        - created_by_id: The ID of the user who created the pick list.
        - user_id: The ID of the user.
        - assigned_user: The name of the assigned user.
        - status: The status of the accession job list.
        - from_dt: The start date.
        - to_dt: The end date.
    - sort_params: The sort parameters.
        - sort_by: The field to sort by.
        - sort_order: The order to sort by.

    **Returns:**
    - list: A paginated list of accession jobs.
    """
    try:
        query = select(AccessionJob)

        if params.queue:
            # queue is the default view on the accession job screen
            # It is not used in advanced search on jobs
            # hide cancelled jobs
            query = query.where(AccessionJob.status != "Cancelled")
            # Filter to exclude Accession Jobs with a related Verification Job not in
            # 'Created' status
            subquery = (
                select(VerificationJob.accession_job_id)
                .where(VerificationJob.status != "Created")
                .distinct()
            )

            # Construct the main query
            query = query.where(
                # Use NOT EXISTS to exclude AccessionJobs with related VerificationJobs not in 'created' status
                or_(
                    AccessionJob.id.not_in(subquery),
                    # AccessionJobs without related VerificationJobs not in 'created' status
                    not_(subquery.exists()),  # Or no related VerificationJobs at all
                )
            )
        if params.status and len(list(filter(None, params.status))) > 0:
            query = query.where(AccessionJob.status.in_(params.status))
        if params.workflow_id:
            query = query.where(AccessionJob.workflow_id == params.workflow_id)
        if params.user_id:
            query = query.where(AccessionJob.user_id.in_(params.user_id))
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
            query = query.where(AccessionJob.user_id.in_(assigned_user_subquery))
        if params.container_type:
            subquery = (
                select(ContainerType.id)
                .where(ContainerType.type == params.container_type)
                .distinct()
            )
            query = query.where(AccessionJob.container_type_id == subquery)
        if params.trayed is not None:
            query = query.where(AccessionJob.trayed == params.trayed)
        if params.created_by_id:
            query = query.where(AccessionJob.created_by_id == params.created_by_id)
        if params.from_dt:
            query = query.where(AccessionJob.create_dt >= params.from_dt)
        if params.to_dt:
            query = query.where(AccessionJob.create_dt <= params.to_dt)

        # Validate and Apply sorting based on sort_params
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

    **Args:**
    - id: The ID of the accession job.

    **Returns:**
    - Accession Job Detail Output: The accession job detail.

    **Raises:**
    - HTTPException: If the accession job with the given ID is not found.
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

    **Args:**
    - id: The ID of the accession job workflow.

    **Returns:**
    - Accession Job Detail Output: The accession job detail.

    **Raises:**
    - HTTPException: If the accession job with the given ID is not found.
    """
    accession_job = session.exec(
        select(AccessionJob).where(AccessionJob.workflow_id == id)
    ).first()

    if accession_job:
        return accession_job

    raise NotFound(detail=f"Accession Job ID {id} Not Found")


@router.post("/", response_model=AccessionJobDetailOutput, status_code=201)
def create_accession_job(
    accession_job_input: AccessionJobInput, session: Session = Depends(get_session)
) -> AccessionJob:
    """
    Create a new accession job:

    **Args:**
    - Accession Job Input: The input data for creating the
    accession job.

    **Returns:**
    - Accession Job: The created accession job.

    **Raises:**
    - HTTPException: If there is an integrity error during the creation of the
    accession job.
    """
    try:
        new_accession_job = AccessionJob(**accession_job_input.model_dump())
        # Set container_type_id based on trayed status
        if new_accession_job.trayed:
            container_type = (
                session.query(ContainerType)
                .filter(ContainerType.type == "Tray")
                .first()
            )
        else:
            container_type = (
                session.query(ContainerType)
                .filter(ContainerType.type == "Non-Tray")
                .first()
            )
        new_accession_job.container_type_id = container_type.id

        # generate a new workflow and attach
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

        return new_accession_job

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=AccessionJobDetailOutput)
def update_accession_job(
    id: int,
    accession_job: AccessionJobUpdateInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
):
    """
    Update an existing accession job with the provided data.

    ***Parameters:**
    - id: The ID of the accession job to be updated.
    - accession job: The data to update the accession job with.

    **Returns:**
    - HTTPException: If the accession job is not found or if an error occurs during
    the update.
    """
    existing_accession_job = session.get(AccessionJob, id)

    # capture original status for process check
    original_status = existing_accession_job.status

    if not existing_accession_job:
        raise NotFound(detail=f"Accession Job ID {id} Not Found")

    mutated_data = accession_job.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_accession_job, key, value)

    # setting the update_dt to now
    setattr(existing_accession_job, "update_dt", datetime.now(timezone.utc))
    # Update container_type_id based on trayed status
    if existing_accession_job.trayed:
        container_type = (
            session.query(ContainerType).filter(ContainerType.type == "Tray").first()
        )
    else:
        container_type = (
            session.query(ContainerType)
            .filter(ContainerType.type == "Non-Tray")
            .first()
        )
    setattr(existing_accession_job, "container_type_id", container_type.id)

    existing_accession_job = commit_record(session, existing_accession_job)

    # conditional to avoid transaction concurrency issues
    if mutated_data.get("status") == "Completed":
        if existing_accession_job.items:
            items_barcode_ids = [
                item.barcode_id for item in existing_accession_job.items
            ]

            session.query(Barcode).filter(
                Barcode.id.in_(items_barcode_ids), Barcode.withdrawn == True
            ).update(
                {"withdrawn": False, "update_dt": datetime.now(timezone.utc)},
                synchronize_session=False,
            )

        if existing_accession_job.non_tray_items:
            non_tray_items_barcode_ids = [
                item.barcode_id for item in existing_accession_job.non_tray_items
            ]

            session.query(Barcode).filter(
                Barcode.id.in_(non_tray_items_barcode_ids), Barcode.withdrawn == True
            ).update(
                {"withdrawn": False, "update_dt": datetime.now(timezone.utc)},
                synchronize_session=False,
            )
        if existing_accession_job.trays:
            trays_barcode_ids = [
                tray.barcode_id for tray in existing_accession_job.trays
            ]

            session.query(Barcode).filter(
                Barcode.id.in_(trays_barcode_ids), Barcode.withdrawn == True
            ).update(
                {"withdrawn": False, "update_dt": datetime.now(timezone.utc)},
                synchronize_session=False,
            )

            for tray in existing_accession_job.trays:
                if tray.items:
                    items_barcode_ids = [item.barcode_id for item in tray.items]

                    session.query(Barcode).filter(
                        Barcode.id.in_(items_barcode_ids), Barcode.withdrawn == True
                    ).update(
                        {"withdrawn": False, "update_dt": datetime.now(timezone.utc)},
                        synchronize_session=False,
                    )

        audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"}).copy()
        background_tasks.add_task(
            complete_accession_job,
            existing_accession_job, 
            original_status,
            audit_info=audit_info
        )
        session.refresh(existing_accession_job)
    else:
        audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"}).copy()
        background_tasks.add_task(
            manage_accession_job_transition,
            existing_accession_job,
            original_status,
            audit_info=audit_info
        )

        session.commit()
        session.refresh(existing_accession_job)

    return existing_accession_job


@router.delete("/{id}", status_code=204)
def delete_accession_job(id: int, session: Session = Depends(get_session)):
    """
    Delete an accession job by its ID.
    **Args:**
    - id: The ID of the accession job to be deleted.

    **Returns:**
    - HTTPException: An HTTP exception indicating the result of the deletion.
    """
    accession_job = session.get(AccessionJob, id)

    if accession_job:
        session.delete(accession_job)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Accession Job id {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Accession Job ID {id} Not Found")
