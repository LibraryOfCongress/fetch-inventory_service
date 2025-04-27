from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.filter_params import JobFilterParams
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.shelf_types import ShelfType
from app.models.size_class import SizeClass
from app.models.trays import Tray
from app.tasks import (
    complete_verification_job,
    manage_verification_job_transition,
    handle_size_class_assigned_status,
)
from app.models.verification_jobs import VerificationJob, VerificationJobStatus
from app.schemas.verification_jobs import (
    VerificationJobInput,
    VerificationJobUpdateInput,
    VerificationJobListOutput,
    VerificationJobDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

router = APIRouter(
    prefix="/verification-jobs",
    tags=["verification jobs"],
)


@router.get("/", response_model=Page[VerificationJobListOutput])
def get_verification_job_list(
    unshelved: bool | None = False,
    queue: bool = Query(default=False),
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    status: VerificationJobStatus | None = None
) -> list:
    """
    Retrieve a paginated list of verification jobs.

    **Returns:**
    - Verification Job List Output: The paginated list of verification jobs.
    """
    query = select(VerificationJob).distinct()

    if unshelved:
        # retrieve completed verification jobs that haven't been shelved
        query = query.where(
            VerificationJob.shelving_job_id == None
        ).where(
            VerificationJob.status == "Completed"
        )
    if queue:
        # filter out completed.  maybe someday hide cancelled.
        query = query.where(VerificationJob.status != "Completed")
    if params.workflow_id:
        query = query.where(VerificationJob.workflow_id == params.workflow_id)
    if params.user_id:
        query = query.where(VerificationJob.user_id == params.user_id)
    if params.created_by_id:
        query = query.where(VerificationJob.created_by_id == params.created_by_id)
    if params.from_dt:
        query = query.where(VerificationJob.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(VerificationJob.create_dt <= params.to_dt)
    if status:
        query = query.where(VerificationJob.status == status.value)

    return paginate(session, query)


@router.get("/{id}", response_model=VerificationJobDetailOutput)
def get_verification_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the verification job detail for the given ID.

    **Args:**
    - ID: The ID of the verification job.

    **Returns:**
    - Verification Job Detail Output: The verification job detail.

    **Raises:**
    - HTTPException: If the verification job with the given ID is not found.
    """
    verification_job = session.get(VerificationJob, id)

    if verification_job:
        return verification_job

    raise NotFound(detail=f"Verification Job ID {id} Not Found")


@router.get("/workflow/{id}", response_model=VerificationJobDetailOutput)
def get_verification_job_detail_by_workflow(
    id: int, session: Session = Depends(get_session)
):
    """
    Retrieves the verification job detail for the given workflow ID.

    **Args:**
    - ID: The ID of the verification job workflow.

    **Returns:**
    - Verification Job Detail Output: The verification job detail.

    **Raises:**
    - HTTPException: If the verification job with the given ID is not found.
    """
    verification_job = session.exec(
        select(VerificationJob).where(VerificationJob.workflow_id == id)
    ).first()

    if verification_job:
        return verification_job

    raise NotFound(detail=f"Verification Job ID {id} Not Found")


@router.post("/", response_model=VerificationJobDetailOutput, status_code=201)
def create_verification_job(
    verification_job_input: VerificationJobInput,
    session: Session = Depends(get_session),
):
    """
    Create a new verification job:

    **Args:**
    - Verification Job Input: The input data for the
    verification job.

    **Returns:**
    - Verification Job Detail Output: The created verification job.
    """
    try:
        verification_job = VerificationJob(**verification_job_input.model_dump())

        # Check if the size_class_id has already been assigned if not assign it
        if verification_job_input.size_class_id:
            size_class = session.get(SizeClass, verification_job_input.size_class_id)

            if size_class and not size_class.assigned:
                session.query(SizeClass).filter(
                    SizeClass.id == verification_job_input.size_class_id
                ).update({"assigned": True})

        session.add(verification_job)
        session.commit()
        session.refresh(verification_job)

        return verification_job

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=VerificationJobDetailOutput)
def update_verification_job(
    id: int,
    verification_job: VerificationJobUpdateInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
):
    """
    Update a verification job:

    **Args:**
    - id: The ID of the verification job to update.
    - Verification Job Update Input: The updated data for the verification job.

    **Returns:**
    - Verification Job Detail Output: The updated verification job.

    **Raises:**
    - HTTPException: If the verification job with the given ID does not exist.
    """
    try:
        existing_verification_job = session.get(VerificationJob, id)

        # capture original status for process check
        original_status = existing_verification_job.status

        # Check if the tray record exists
        if not existing_verification_job:
            raise NotFound(detail=f"Verification Job ID {id} Not Found")

        # Update the tray record with the mutated data
        mutated_data = verification_job.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_verification_job, key, value)

        setattr(existing_verification_job, "update_dt", datetime.utcnow())

        existing_verification_job = commit_record(session, existing_verification_job)

        # Check if size class has already been assigned
        if verification_job.size_class_id and (
            verification_job.size_class_id != existing_verification_job.size_class_id
        ):
            updated_size_class = session.get(SizeClass, verification_job.size_class_id)
            if updated_size_class and not updated_size_class.assigned:
                session.query(SizeClass).filter(
                    SizeClass.id == verification_job.size_class_id
                ).update({"assigned": True}, synchronize_session=False)
            else:
                background_tasks.add_task(
                    handle_size_class_assigned_status(
                        session,
                        updated_size_class,
                        VerificationJob,
                        existing_verification_job,
                    )
                )

        if mutated_data.get("status") == "Completed":
            background_tasks.add_task(
                complete_verification_job, session, existing_verification_job
            )
        else:
            background_tasks.add_task(
                manage_verification_job_transition,
                session,
                existing_verification_job,
                original_status,
            )

            session.refresh(existing_verification_job)

        return existing_verification_job

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_verification_job(id: int, session: Session = Depends(get_session)):
    """
    Delete a verification job by its ID.

    **Args:**
    - id: The ID of the verification job to delete.

    **Returns:**
    - HTTPException: An HTTP exception indicating the result of the deletion.
    """
    verification_job = session.get(VerificationJob, id)

    if verification_job:
        # Check if size class has already been assigned
        size_class = session.get(SizeClass, verification_job.size_class_id)
        handle_size_class_assigned_status(
            session, size_class, VerificationJob, verification_job
        )

        session.delete(verification_job)
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Verification Job id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Verification Job ID {id} Not Found")
