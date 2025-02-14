from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select

from app.config.exceptions import BadRequest, NotFound
from app.database.session import get_session, commit_record
from app.models.verification_changes import VerificationChange
from app.schemas.verification_changes import (
    VerificationChangeInput,
    VerificationChangeUpdateInput,
    VerificationChangeListOutput,
    VerificationChangeDetailOutput,
)

router = APIRouter(
    prefix="/verification-changes",
    tags=["verification changes"],
)


@router.get("/", response_model=Page[VerificationChangeListOutput])
def get_verification_change_list(session: Session = Depends(get_session)):
    """
    Retrieve a paginated list of verification changes.

    **Returns:**
    - Verification Change List Output: The paginated list of verification changes.
    """
    return paginate(session, select(VerificationChange))


@router.get("/{id}", response_model=VerificationChangeDetailOutput)
def get_verification_change_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the verification job detail for the given workflow ID.

    **Args:**
    - ID: The ID of the verification job workflow.

    **Returns:**
    - Verification Job Detail Output: The verification job detail.

    **Raises:**
    - HTTPException: If the verification job with the given ID is not found.
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

    **Args:**
    - Verification Change Input: The input data for the
    verification change.

    **Returns:**
    - Verification Change Detail Output: The created verification change.
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

    **Args:**
    - id: The ID of the verification change to update.
    - Verification Change Update Input: The updated data for the verification change.

    **Returns:**
    - Verification Change Detail Output: The updated verification change.

    **Raises:**
    - HTTPException: If the verification change with the given ID does not exist.
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

    **Args:**
    - id: The ID of the verification change to delete.

    **Returns:**
    - HTTPException: An HTTP exception indicating the result of the deletion.
    """
    existing_verification_change = session.get(VerificationChange, id)

    if existing_verification_change:
        session.delete(existing_verification_change)
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Verification Change id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Verification Change ID {id} Not Found")
