from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.shelving_jobs import ShelvingJob
from app.schemas.shelving_jobs import (
    ShelvingJobInput,
    ShelvingJobUpdateInput,
    ShelvingJobListOutput,
    ShelvingJobDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

router = APIRouter(
    prefix="/shelving-jobs",
    tags=["shelving jobs"],
)


@router.get("/", response_model=Page[ShelvingJobListOutput])
def get_shelving_job_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of shelving jobs.

    **Returns:**
    - list: A paginated list of shelving jobs.
    """
    return paginate(session, select(ShelvingJob))


@router.get("/{id}", response_model=ShelvingJobDetailOutput)
def get_shelving_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the shelving job detail for the given ID.

    **Args:**
    - id: The ID of the shelving job.

    **Returns:**
    - Shelving Job Detail Output: The shelving job detail.

    **Raises:**
    - HTTPException: If the shelving job with the given ID is not found.
    """
    shelving_job = session.get(ShelvingJob, id)

    if shelving_job:
        return shelving_job

    raise NotFound(detail=f"Shelving Job ID {id} Not Found")


@router.post("/", response_model=ShelvingJobDetailOutput, status_code=201)
def create_shelving_job(
    shelving_job_input: ShelvingJobInput, session: Session = Depends(get_session)
) -> ShelvingJob:
    """
    Create a new shelving job:

    **Args:**
    - Shelving Job Input: The input data for creating the
    shelving job.

    **Returns:**
    - Shelving Job: The created shelving job.

    **Raises:**
    - HTTPException: If there is an integrity error during the creation of the
    shelving job.
    """

    try:
        new_shelving_job = ShelvingJob(**shelving_job_input.model_dump())
        session.add(new_shelving_job)
        session.commit()
        session.refresh(new_shelving_job)

        return new_shelving_job

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=ShelvingJobDetailOutput)
def update_shelving_job(
    id: int,
    shelving_job: ShelvingJobUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update an existing shelving job with the provided data.

    ***Parameters:**
    - id: The ID of the shelving job to be updated.
    - shelving job: The data to update the shelving job with.

    **Returns:**
    - HTTPException: If the shelving job is not found or if an error occurs during
    the update.
    """
    try:
        existing_shelving_job = session.get(ShelvingJob, id)

        if not existing_shelving_job:
            raise NotFound(detail=f"Shelving Job ID {id} Not Found")

        mutated_data = shelving_job.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_shelving_job, key, value)

        setattr(existing_shelving_job, "update_dt", datetime.utcnow())

        session.add(existing_shelving_job)
        session.commit()
        session.refresh(existing_shelving_job)

        return existing_shelving_job

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_shelving_job(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelving job by its ID.
    **Args:**
    - id: The ID of the shelving job to be deleted.

    **Returns:**
    - HTTPException: An HTTP exception indicating the result of the deletion.
    """
    shelving_job = session.get(ShelvingJob, id)
    if shelving_job:
        session.delete(shelving_job)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Shelving Job id {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Shelving Job ID {id} Not Found")


