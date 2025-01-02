from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.filter_params import JobFilterParams, SortParams
from app.tasks import (
    complete_verification_job,
    manage_verification_job_transition,
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
from app.utilities import get_sorted_query

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
    status: VerificationJobStatus | None = None,
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of verification jobs.

    **Parameters:**
    - unshelved: Filters out shelved verification jobs.
    - queue: Filters out cancelled verification jobs.
    - params: The filter parameters.
    - status: The status of the verification job.
    - sort_params: The sort parameters.

    **Returns:**
    - Verification Job List Output: The paginated list of verification jobs.
    """
    # Create a query to select all Verification Job from the database
    query = select(VerificationJob).distinct()

    if unshelved:
        # retrieve completed verification jobs that haven't been shelved
        query = query.where(VerificationJob.shelving_job_id == None).where(
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

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(VerificationJob, query, sort_params)

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
        session.delete(verification_job)
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Verification Job id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Verification Job ID {id} Not Found")
