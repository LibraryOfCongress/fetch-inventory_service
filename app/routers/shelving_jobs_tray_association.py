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
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
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
    "/tray-association/{shelving_job_id}/{tray_id}",
    response_model=ShelvingJobTrayAssociationDetailOutput,
)
def get_shelving_job_tray_association_detail(
    shelving_job_id: int, tray_id: int, session: Session = Depends(get_session)
):
    """
    Retrieves the shelving job detail tray association for the given ID.

    **Args:**
    - shelving job id: The ID of the shelving job association.
    - tray id: The ID of the tray association.

    **Returns:**
    - Shelving Job Tray Association Detail Output: The shelving job tray association
    detail.

    **Raises:**
    - HTTPException: If the shelving job tray association with the given ID is not found.
    """

    statements = (
        select(ShelvingJobTrayAssociation)
        .where(ShelvingJobTrayAssociation.shelving_job_id == shelving_job_id)
        .where(ShelvingJobTrayAssociation.tray_id == tray_id)
    )

    shelving_job_tray_association = session.exec(statements).first()

    if shelving_job_tray_association:
        return shelving_job_tray_association

    raise NotFound(detail=f"Shelving Job Tray Association ID {id} Not Found")


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
    try:
        new_shelving_job_tray_association = ShelvingJobTrayAssociation(
            **shelving_job_input.model_dump()
        )
        session.add(new_shelving_job_tray_association)
        session.commit()
        session.refresh(new_shelving_job_tray_association)

        return new_shelving_job_tray_association

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch(
    "/tray-association/{shelving_job_id}/{tray_id}",
    response_model=ShelvingJobTrayAssociationDetailOutput,
)
def update_shelving_job_tray_association(
    shelving_job_id: int,
    tray_id: int,
    shelving_job_tray_association: ShelvingJobTrayAssociationUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update an existing shelving job tray association with the provided data.

    ***Parameters:**
    - shelving job id: The ID of the shelving job association to be updated.
    - tray id: The ID of the tray association to be updated.
    - shelving job tray association: The data to update the shelving job tray
    association with.

    **Returns:**
    - HTTPException: If the shelving job tray association is not found or if an error
    occurs during the update.
    """
    try:
        statements = (
            select(ShelvingJobTrayAssociation)
            .where(ShelvingJobTrayAssociation.shelving_job_id == shelving_job_id)
            .where(ShelvingJobTrayAssociation.tray_id == tray_id)
        )

        existing_shelving_job_tray_association = session.exec(statements).first()

        if not existing_shelving_job_tray_association:
            raise NotFound(detail=f"Shelving Job Tray Association ID {id} Not Found")

        mutated_data = shelving_job_tray_association.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_shelving_job_tray_association, key, value)

        setattr(existing_shelving_job_tray_association, "update_dt", datetime.utcnow())

        session.add(existing_shelving_job_tray_association)
        session.commit()
        session.refresh(existing_shelving_job_tray_association)

        return existing_shelving_job_tray_association

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/tray-association/{shelving_job_id}/{tray_id}", status_code=204)
def delete_shelving_job_tray_association(
    shelving_job_id: int, tray_id: int, session: Session = Depends(get_session)
):
    """
    Delete a shelving job tray association by its ID.
    **Args:**
    - shelving job id: The ID of the shelving job association to be deleted.
    - tray id: The ID of the tray association to be deleted.

    **Returns:**
    - HTTPException: An HTTP exception indicating the result of the deletion.
    """
    statement = (
        select(ShelvingJobTrayAssociation)
        .where(ShelvingJobTrayAssociation.shelving_job_id == shelving_job_id)
        .where(ShelvingJobTrayAssociation.tray_id == tray_id)
    )

    shelving_job_tray_association = session.exec(statement).first()

    if shelving_job_tray_association:
        session.delete(shelving_job_tray_association)
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Shelving Job Tray Association id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Shelving Job Tray Association ID {id} Not Found")
