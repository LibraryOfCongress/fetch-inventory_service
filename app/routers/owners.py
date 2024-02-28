from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.owners import Owner
from app.models.owner_tiers import OwnerTier
from app.schemas.owners import (
    OwnerInput,
    OwnerUpdateInput,
    OwnerListOutput,
    OwnerDetailWriteOutput,
    OwnerDetailReadOutput,
)


router = APIRouter(
    prefix="/owners",
    tags=["owners"],
)


@router.get("/", response_model=Page[OwnerListOutput])
def get_owner_list(session: Session = Depends(get_session)) -> list:
    """
    Get a list of owners.

    **Returns:**
    - Owner List Output: The paginated list of owners.
    """
    return paginate(session, select(Owner))


@router.get("/{id}", response_model=OwnerDetailReadOutput)
def get_owner_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve owner details by ID.

    **Args:**
    - id: The ID of the owner to retrieve.

    **Returns:**
    - Owner Detail Read Output: The owner details.

    **Raises:**
    - HTTPException: If the owner is not found.
    """
    owner = session.get(Owner, id)
    if owner:
        return owner
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=OwnerDetailWriteOutput, status_code=201)
def create_owner(
    owner_input: OwnerInput, session: Session = Depends(get_session)
) -> Owner:
    """
    Create an owner:

    **Args:**
    - Owner Input: The input data for creating the owner.

    **Returns:**
    - Owner Detail Write Output: The created owner.

    **Raises:**
    - None

    **Notes:**
    - **name**: Required string
    - **owner_tier_id**: Required integer id for related owner tier
    - **parent_owner_id**: Optional integer id for parent_owner
    """
    new_owner = Owner(**owner_input.model_dump())

    # Check if the parent_owner_id is set
    if new_owner.parent_owner_id is not None:
        # Retrieve the parent owner
        parent_owner = session.exec(
            select(Owner).where(Owner.id == new_owner.parent_owner_id)
        ).first()
        if parent_owner is None:
            raise HTTPException(status_code=404, detail="Parent owner not found")

        # query new_owner.owner_tier to get proposed tier level
        new_owner_tier_level = (
            session.exec(
                select(OwnerTier).where(OwnerTier.id == new_owner.owner_tier_id)
            )
            .first()
            .level
        )

        # Check if the owner_tier is greater than the parent's owner_tier
        if new_owner_tier_level <= parent_owner.owner_tier.level:
            raise HTTPException(
                status_code=400,
                detail="Owner tier must be lower level (higher value) than parent owner's tier",
            )

    # Add the new owner to the database
    session.add(new_owner)
    session.commit()
    session.refresh(new_owner)
    return new_owner


@router.patch("/{id}", response_model=OwnerDetailWriteOutput)
def update_owner(
    id: int, owner: OwnerUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an existing owner.

    **Args:**
    - id: The ID of the owner to be updated.
    - Owner Update Input: The updated owner information.

    **Returns:**
    - Owner Detail Write Output: The updated owner object.

    Raises:
    - HTTPException: If the owner with the given ID is not found.
    - HTTPException: If an error occurs during the update process.
    """
    existing_owner = session.get(Owner, id)

    if existing_owner is None:
        raise HTTPException(status_code=404)

    mutated_data = owner.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_owner, key, value)

    # Check if the parent_owner_id is set
    if existing_owner.parent_owner_id is not None:
        # Retrieve the parent owner
        parent_owner = session.exec(
            select(Owner).where(Owner.id == existing_owner.parent_owner_id)
        ).first()
        if parent_owner is None:
            raise HTTPException(status_code=404, detail="Parent owner not found")

        # Check if the owner_tier is greater than the parent's owner_tier
        if existing_owner.owner_tier.level <= parent_owner.owner_tier.level:
            raise HTTPException(
                status_code=400,
                detail="Owner tier must be lower level (higher value) than parent owner's tier",
            )

    setattr(existing_owner, "update_dt", datetime.utcnow())
    session.add(existing_owner)
    session.commit()
    session.refresh(existing_owner)
    return existing_owner


@router.delete("/{id}")
def delete_owner(id: int, session: Session = Depends(get_session)):
    """
    Delete an owner by their ID.

    **Args:**
    - id: The ID of the owner to delete.

    **Returns:**
    - None

    **Raises:**
    - HTTPException: If the owner with the given ID does not exist.
    """
    owner = session.get(Owner, id)

    if owner:
        session.delete(owner)
        session.commit()
        return HTTPException(status_code=204)
    else:
        raise HTTPException(status_code=404)
