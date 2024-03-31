from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy import not_, and_, or_
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.models.accession_jobs import AccessionJob
from app.models.verification_jobs import VerificationJob
from app.models.container_types import ContainerType
from app.tasks import generate_verification_job
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
from app.schemas.verification_jobs import VerificationJobInput

router = APIRouter(
    prefix="/accession-jobs",
    tags=["accession jobs"],
)


@router.get("/", response_model=Page[AccessionJobListOutput])
def get_accession_job_list(
    queue: bool = Query(default=False), session: Session = Depends(get_session)
) -> list:
    """
    Retrieve a paginated list of accession jobs.

    **Returns:**
    - list: A paginated list of accession jobs.
    """
    try:
        query = select(AccessionJob)

        if queue:
            # Filter to exclude Accession Jobs with a related Verification Job not in
            # 'Created' status
            subquery = (
                select(VerificationJob.accession_job_id)
                .where(VerificationJob.status != "Created")
                .distinct()
            )

            # Construct the main query
            query = select(AccessionJob).where(
                # Use NOT EXISTS to exclude AccessionJobs with related VerificationJobs not in 'created' status
                or_(
                    AccessionJob.id.not_in(subquery),
                    # AccessionJobs without related VerificationJobs not in 'created' status
                    not_(subquery.exists()),  # Or no related VerificationJobs at all
                )
            )

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
            container_type = session.query(ContainerType).filter(
                ContainerType.type == 'Tray'
            ).first()
        else:
            container_type = session.query(ContainerType).filter(
                ContainerType.type == 'Non-Tray'
            ).first()
        new_accession_job.container_type_id = container_type.id
        session.add(new_accession_job)
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

    if not existing_accession_job:
        raise NotFound(detail=f"Accession Job ID {id} Not Found")

    mutated_data = accession_job.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_accession_job, key, value)

    # setting the update_dt to now
    setattr(existing_accession_job, "update_dt", datetime.utcnow())
    # Update container_type_id based on trayed status
    if existing_accession_job.trayed:
        container_type = session.query(ContainerType).filter(
            ContainerType.type == 'Tray'
        ).first()
    else:
        container_type = session.query(ContainerType).filter(
            ContainerType.type == 'Non-Tray'
        ).first()
    setattr(existing_accession_job, "container_type_id", container_type.id)

    existing_accession_job = commit_record(session, existing_accession_job)

    if mutated_data.get("status") == "Completed":
        # Automatically create a related Verification Job.
        background_tasks.add_task(
            generate_verification_job, session, existing_accession_job
        )

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
