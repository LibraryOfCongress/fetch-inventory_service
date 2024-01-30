from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.shelving_jobs import ShelvingJobTrayAssociation
from app.schemas.shelving_jobs_tray_association import (
    ShelvingJobTrayAssociationInput,
    ShelvingJobTrayAssociationUpdateInput,
    ShelvingJobTrayAssociationListOutput,
    ShelvingJobTrayAssociationDetailOutput,
)

router = APIRouter(
    prefix="/shelving-jobs",
    tags=["shelving jobs tray association"],
)


@router.get(
    "/tray-association", response_model=Page[ShelvingJobTrayAssociationListOutput]
)
def get_shelving_job_tray_association_list(
    session: Session = Depends(get_session),
) -> list:
    """
    Retrieve a paginated list of shelving jobs tray association.

    **Returns:**
    - list: A paginated list of shelving jobs tray association.
    """
    return paginate(session, select(ShelvingJobTrayAssociation))


@router.get(
    "/tray-association/{id}", response_model=ShelvingJobTrayAssociationDetailOutput
)
def get_shelving_job_tray_association_detail(
    id: int, session: Session = Depends(get_session)
):
    """
    Retrieves the shelving job detail tray association for the given ID.

    **Args:**
    - id: The ID of the shelving job tray association.

    **Returns:**
    - Shelving Job Tray Association Detail Output: The shelving job tray association
    detail.

    **Raises:**
    - HTTPException: If the shelving job tray association with the given ID is not found.
    """
    shelving_job_tray_association = session.get(ShelvingJobTrayAssociation, id)
    if shelving_job_tray_association:
        return shelving_job_tray_association
    else:
        raise HTTPException(status_code=404)


@router.post(
    "/tray-association",
    response_model=ShelvingJobTrayAssociationDetailOutput,
    status_code=201,
)
def create_shelving_job_tray_association(
    shelving_job_input: ShelvingJobTrayAssociationInput,
    session: Session = Depends(get_session),
) -> ShelvingJobTrayAssociation:
    """
    Create a new shelving job:

    **Args:**
    - Shelving Job Tray Association Input: The input data for creating the
    shelving job tray association.

    **Returns:**
    - Shelving Job Tray Association: The created shelving job tray association.

    **Raises:**
    - HTTPException: If there is an integrity error during the creation of the
    shelving job tray association.
    """

    new_shelving_job_tray_association = ShelvingJobTrayAssociation(
        **shelving_job_input.model_dump()
    )
    session.add(new_shelving_job_tray_association)
    session.commit()
    session.refresh(new_shelving_job_tray_association)

    return new_shelving_job_tray_association


@router.patch(
    "/tray-association/{id}", response_model=ShelvingJobTrayAssociationDetailOutput
)
def update_shelving_job_tray_association(
    id: int,
    shelving_job_tray_association: ShelvingJobTrayAssociationUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update an existing shelving job tray association with the provided data.

    ***Parameters:**
    - id: The ID of the shelving job tray association to be updated.
    - shelving job tray association: The data to update the shelving job tray
    association with.

    **Returns:**
    - HTTPException: If the shelving job tray association is not found or if an error
    occurs during the update.
    """

    existing_shelving_job_tray_association = session.get(ShelvingJobTrayAssociation, id)

    if not existing_shelving_job_tray_association:
        raise HTTPException(status_code=404)

    mutated_data = shelving_job_tray_association.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_shelving_job_tray_association, key, value)

    setattr(existing_shelving_job_tray_association, "update_dt", datetime.utcnow())

    session.add(existing_shelving_job_tray_association)
    session.commit()
    session.refresh(existing_shelving_job_tray_association)

    return existing_shelving_job_tray_association


@router.delete("/tray-association/{id}", status_code=204)
def delete_shelving_job_tray_association(
    id: int, session: Session = Depends(get_session)
):
    """
    Delete a shelving job tray association by its ID.
    **Args:**
    - id: The ID of the shelving job tray association to be deleted.

    **Returns:**
    - HTTPException: An HTTP exception indicating the result of the deletion.
    """
    shelving_job_tray_association = session.get(ShelvingJobTrayAssociation, id)
    if shelving_job_tray_association:
        session.delete(shelving_job_tray_association)
        session.commit()
    else:
        raise HTTPException(status_code=404)

    return HTTPException(
        status_code=204,
        detail=f"Shelving Job Tray Association id {id} deleted " f"successfully",
    )
