from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.verification_jobs import VerificationJob
from app.schemas.verification_jobs import (
    VerificationJobInput,
    VerificationJobUpdateInput,
    VerificationJobListOutput,
    VerificationJobDetailOutput,
)

router = APIRouter(
    prefix="/verification-jobs",
    tags=["verification jobs"],
)


@router.get("/", response_model=Page[VerificationJobListOutput])
def get_verification_job_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of verification jobs.

    **Returns:**
    - Verification Job List Output: The paginated list of verification jobs.
    """
    return paginate(session, select(VerificationJob))


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
    else:
        raise HTTPException(status_code=404)


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
    verification_job = VerificationJob(**verification_job_input.model_dump())
    session.add(verification_job)
    session.commit()
    session.refresh(verification_job)
    return verification_job


@router.patch("/{id}", response_model=VerificationJobDetailOutput)
def update_verification_job(
    id: int,
    verification_job: VerificationJobUpdateInput,
    session: Session = Depends(get_session),
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
    existing_verification_job = session.get(VerificationJob, id)

    if existing_verification_job:
        mutated_data = verification_job.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_verification_job, key, value)

        setattr(existing_verification_job, "update_dt", datetime.utcnow())

        session.commit()
        session.refresh(existing_verification_job)
        return existing_verification_job
    else:
        raise HTTPException(status_code=404)


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
        return HTTPException(status_code=204)
    else:
        raise HTTPException(status_code=404)
