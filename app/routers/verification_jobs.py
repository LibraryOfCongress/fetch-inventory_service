from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.tasks import complete_verification_job
from app.models.verification_jobs import VerificationJob
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
def get_verification_job_list(unshelved: bool | None = False, session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of verification jobs.

    **Returns:**
    - Verification Job List Output: The paginated list of verification jobs.
    """
    if unshelved:
        verification_job_list = select(VerificationJob).where(
            VerificationJob.shelving_job_id == None
        ).where(VerificationJob.status == "Completed")
    else:
        verification_job_list = select(VerificationJob)
    return paginate(session, verification_job_list)


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

        # Check if the tray record exists
        if not existing_verification_job:
            raise NotFound(detail=f"Verification Job ID {id} Not Found")

        # Update the tray record with the mutated data
        mutated_data = verification_job.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_verification_job, key, value)

        setattr(existing_verification_job, "update_dt", datetime.utcnow())

        session.commit()
        session.refresh(existing_verification_job)
        session.refresh(existing_verification_job)

        if mutated_data.get("status") == "Completed":
            background_tasks.add_task(
                complete_verification_job, session, existing_verification_job
            )

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
