from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.models.accession_jobs import AccessionJob
from app.tasks import generate_verification_job

from app.schemas.accession_jobs import (
    AccessionJobInput,
    AccessionJobUpdateInput,
    AccessionJobListOutput,
    AccessionJobDetailOutput,
)
from app.schemas.verification_jobs import VerificationJobInput

router = APIRouter(
    prefix="/accession-jobs",
    tags=["accession jobs"],
)


@router.get("/", response_model=Page[AccessionJobListOutput])
def get_accession_job_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of accession jobs.

    **Returns:**
    - list: A paginated list of accession jobs.
    """
    return paginate(session, select(AccessionJob))


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
    else:
        raise HTTPException(status_code=404)


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
        session.add(new_accession_job)
        session.commit()
        session.refresh(new_accession_job)

        return new_accession_job

    except IntegrityError as e:
        raise HTTPException(status_code=422, detail=f"{e}")


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
    try:
        existing_accession_job = session.get(AccessionJob, id)

        if not existing_accession_job:
            raise HTTPException(status_code=404)

        mutated_data = accession_job.model_dump(exclude_unset=True)

        if mutated_data.get("status") == "Completed":
            # Automatically create a related Verification Job.
            background_tasks.add_task(
                generate_verification_job, session, existing_accession_job
            )

        for key, value in mutated_data.items():
            setattr(existing_accession_job, key, value)

        setattr(existing_accession_job, "update_dt", datetime.utcnow())
        existing_accession_job = commit_record(session, existing_accession_job)

        return existing_accession_job
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


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
    else:
        raise HTTPException(status_code=404)

    return HTTPException(
        status_code=204, detail=f"Accession Job id {id} deleted successfully"
    )
