from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.owners import Owner
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
    Retrieve a paginated list of owners.

    **Returns:**
    - A list of Owner List Output objects representing the owners.
    """
    return paginate(session, select(Owner))


@router.get("/{id}", response_model=OwnerDetailReadOutput)
def get_owner_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve owner details by ID

    **Args:**
    - id (int): The ID of the owner

    **Returns:**
    - Owner Detail Read Output: The owner details

    **Raises:**
    - HTTPException: If the owner is not found
    """
    owner = session.get(Owner, id)
    if owner:
        return owner
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=OwnerDetailWriteOutput)
def create_owner(
    owner_input: OwnerInput, session: Session = Depends(get_session)
) -> Owner:
    """
    Create a owner:

    **Args:**
    - Owner Input: An instance of OwnerInput, containing the input data for creating
    the owner.

    **Returns:**
    - Owner Detail Write Output: The newly created owner.

    **Notes:**
    - **name**: Required string
    - **owner_tier_id**: Required integer id for related owner tier
    """
    new_owner = Owner(**owner_input.model_dump())
    session.add(new_owner)
    session.commit()
    session.refresh(new_owner)
    return new_owner


@router.patch("/{id}", response_model=OwnerDetailWriteOutput)
def update_owner(
    id: int, owner: OwnerUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an existing owner with the provided data.

    **Args:**
    - id (int): The ID of the owner to update.
    - Owner Update Input: The data to update the owner with.

    **Returns:**
    - Owner Detail Write Output: The updated owner.

    **Raises:**
    - HTTPException: If the owner is not found.
    """
    try:
        existing_owner = session.get(Owner, id)

        if not existing_owner:
            raise HTTPException(status_code=404)

        mutated_data = owner.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_owner, key, value)

        setattr(existing_owner, "update_dt", datetime.utcnow())
        session.add(existing_owner)
        session.commit()
        session.refresh(existing_owner)

        return existing_owner
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_owner(id: int, session: Session = Depends(get_session)):
    """
    Delete an owner by ID.

    **Args:**
    - id (int): The ID of the owner to delete.

    **Returns:**
    - None

    **Raises:**
    - HTTPException: If the owner is not found.
    """
    owner = session.get(Owner, id)
    if owner:
        session.delete(owner)
        session.commit()
    else:
        raise HTTPException(status_code=404)
