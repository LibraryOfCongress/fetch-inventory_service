from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.accession_jobs import AccessionJob
from app.schemas.accession_jobs import (
    AccessionJobInput,
    AccessionJobListOutput,
    AccessionJobDetailOutput,
)

router = APIRouter(
    prefix="/accession-jobs",
    tags=["accession jobs"],
)


@router.get("/", response_model=Page[AccessionJobListOutput])
def get_accession_job_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of accession jobs.
    """
    return paginate(session, select(AccessionJob))


@router.get("/{id}", response_model=AccessionJobDetailOutput)
def get_accession_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the accession job detail for the given ID.
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
    id: int, accession_job: AccessionJobInput, session: Session = Depends(get_session)
):
    try:
        existing_accession_job = session.get(AccessionJob, id)

        if not existing_accession_job:
            raise HTTPException(status_code=404)

        mutated_data = accession_job.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_accession_job, key, value)

        setattr(existing_accession_job, "update_dt", datetime.utcnow())

        session.add(existing_accession_job)
        session.commit()
        session.refresh(existing_accession_job)

        return existing_accession_job
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_accession_job(id: int, session: Session = Depends(get_session)):
    """
    Delete an accession job by its ID.
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
