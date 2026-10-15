# /code/app/routers/verification_changes.py - REFACRORED TO SQLALCHEMY V2

from datetime import datetime, timezone

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.filter_params import SortParams
from app.models.verification_changes import VerificationChange
from app.schemas.verification_changes import (
    VerificationChangeInput,
    VerificationChangeUpdateInput,
    VerificationChangeListOutput,
    VerificationChangeDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter, VerificationChangeSorter

from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/verification-changes",
    tags=["verification changes"],
    dependencies=[Depends(RequiresPermission("can_access_verification"))],
)


@router.get("/", response_model=Page[VerificationChangeListOutput])
def get_verification_change_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of verification changes.
    """
    query = select(VerificationChange)
    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = VerificationChangeSorter(VerificationChange)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=VerificationChangeDetailOutput)
def get_verification_change_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the verification job detail for the given workflow ID.
    """
    if not id:
        raise BadRequest(detail="id is required")

    verification_change = session.get(VerificationChange, id)

    if not verification_change:
        raise NotFound(detail=f"Verification Change ID {id} Not Found")

    return verification_change


@router.post("/", response_model=VerificationChangeDetailOutput, status_code=201)
def create_verification_change(
    verification_change_input: VerificationChangeInput,
    session: Session = Depends(get_session),
):
    """
    Create a new verification change:
    """
    new_verification_change = VerificationChange(
        **verification_change_input.model_dump()
    )

    new_verification_change = commit_record(session, new_verification_change)

    return new_verification_change


@router.patch("/{id}", response_model=VerificationChangeDetailOutput)
def update_verification_change(
    id: int,
    verification_change: VerificationChangeUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a verification change:
    """
    existing_verification_change = session.get(VerificationChange, id)

    if not existing_verification_change:
        raise NotFound(detail=f"Verification Change ID {id} Not Found")

    mutated_data = verification_change.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_verification_change, key, value)

    setattr(existing_verification_change, "update_dt", datetime.now(timezone.utc))

    existing_verification_change = commit_record(session, existing_verification_change)

    return existing_verification_change


@router.delete("/{id}", status_code=204)
def delete_verification_change(id: int, session: Session = Depends(get_session)):
    """
    Delete a verification change by its ID.
    """
    existing_verification_change = session.get(VerificationChange, id)

    if existing_verification_change:
        session.delete(existing_verification_change)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Verification Change ID {id} Not Found")
