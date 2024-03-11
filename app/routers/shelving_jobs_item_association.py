from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.shelving_jobs import ShelvingJobItemAssociation
from app.schemas.shelving_jobs_item_association import (
    ShelvingJobItemAssociationInput,
    ShelvingJobItemAssociationUpdateInput,
    ShelvingJobItemAssociationListOutput,
    ShelvingJobItemAssociationDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

router = APIRouter(
    prefix="/shelving-jobs",
    tags=["shelving jobs item association"],
)


@router.get(
    "/item-association", response_model=Page[ShelvingJobItemAssociationListOutput]
)
def get_shelving_job_item_association_list(
    session: Session = Depends(get_session),
) -> list:
    """
    Retrieve a paginated list of shelving jobs item association.

    **Returns:**
    - list: A paginated list of shelving jobs item association.
    """
    return paginate(session, select(ShelvingJobItemAssociation))


@router.get(
    "/item-association/{shelving_job_id}/{item_id}",
    response_model=ShelvingJobItemAssociationDetailOutput,
)
def get_shelving_job_item_association_detail(
    shelving_job_id: int, item_id: int, session: Session = Depends(get_session)
):
    """
    Retrieves the shelving job detail item association for the given ID.

    **Args:**
    - shelving job id: The ID of the shelving job item association.
    - item id: The ID of the item association.

    **Returns:**
    - Shelving Job Item Association Detail Output: The shelving job item association
    detail.

    **Raises:**
    - HTTPException: If the shelving job item association with the given ID is not
    found.
    """
    statements = (
        select(ShelvingJobItemAssociation)
        .where(ShelvingJobItemAssociation.shelving_job_id == shelving_job_id)
        .where(ShelvingJobItemAssociation.item_id == item_id)
    )

    shelving_job_item_association = session.exec(statements).first()

    if shelving_job_item_association:
        return shelving_job_item_association

    raise NotFound(detail=f"Shelving Job Item Association ID {id} Not Found")


@router.post(
    "/item-association",
    response_model=ShelvingJobItemAssociationDetailOutput,
    status_code=201,
)
def create_shelving_job_item_association(
    shelving_job_input: ShelvingJobItemAssociationInput,
    session: Session = Depends(get_session),
) -> ShelvingJobItemAssociation:
    """
    Create a new shelving job:

    **Args:**
    - Shelving Job Item Association Input: The input data for creating the
    shelving job item association.

    **Returns:**
    - Shelving Job Item Association: The created shelving job item association.

    **Raises:**
    - HTTPException: If there is an integrity error during the creation of the
    shelving job item association.
    """
    try:
        new_shelving_job_item_association = ShelvingJobItemAssociation(
            **shelving_job_input.model_dump()
        )
        session.add(new_shelving_job_item_association)
        session.commit()
        session.refresh(new_shelving_job_item_association)

        return new_shelving_job_item_association

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch(
    "/item-association/{shelving_job_id}/{item_id}",
    response_model=ShelvingJobItemAssociationDetailOutput,
)
def update_shelving_job_item_association(
    shelving_job_id: int,
    item_id: int,
    shelving_job_item_association: ShelvingJobItemAssociationUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update an existing shelving job item association with the provided data.

    ***Parameters:**
    - shelving job id: The ID of the shelving job association to be updated.
    - item id: The ID of the item association to be updated.
    - shelving job item association: The data to update the shelving job item
    association with.

    **Returns:**
    - HTTPException: If the shelving job item association is not found or if an error
    occurs during the update.
    """
    try:
        statements = (
            select(ShelvingJobItemAssociation)
            .where(ShelvingJobItemAssociation.shelving_job_id == shelving_job_id)
            .where(ShelvingJobItemAssociation.item_id == item_id)
        )

        existing_shelving_job_item_association = session.exec(statements).first()

        if not existing_shelving_job_item_association:
            raise NotFound(detail=f"Shelving Job Item Association ID {id} Not Found")

        mutated_data = shelving_job_item_association.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_shelving_job_item_association, key, value)

        setattr(existing_shelving_job_item_association, "update_dt", datetime.utcnow())

        session.add(existing_shelving_job_item_association)
        session.commit()
        session.refresh(existing_shelving_job_item_association)

        return existing_shelving_job_item_association

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/item-association/{shelving_job_id}/{item_id}", status_code=204)
def delete_shelving_job_item_association(
    shelving_job_id: int, item_id: int, session: Session = Depends(get_session)
):
    """
    Delete a shelving job item association by its ID.
    **Args:**
    - shelving job id: The ID of the shelving job association to be deleted.
    - item id: The ID of the item association to be deleted.

    **Returns:**
    - HTTPException: An HTTP exception indicating the result of the deletion.
    """
    statements = (
        select(ShelvingJobItemAssociation)
        .where(ShelvingJobItemAssociation.shelving_job_id == shelving_job_id)
        .where(ShelvingJobItemAssociation.item_id == item_id)
    )

    shelving_job_item_association = session.exec(statements).first()

    if shelving_job_item_association:
        session.delete(shelving_job_item_association)
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Shelving Job Item Association id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Shelving Job Item Association ID {id} Not Found")
