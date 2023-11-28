from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.owners import Owner
from app.schemas.owners import (
    OwnerInput,
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
    return paginate(session, select(Owner))


@router.get("/{id}", response_model=OwnerDetailReadOutput)
def get_owner_detail(id: int, session: Session = Depends(get_session)):
    owner = session.get(Owner, id)
    if owner:
        return owner
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=OwnerDetailWriteOutput)
def create_owner(owner_input: OwnerInput, session: Session = Depends(get_session)) -> Owner:
    """
    Create a owner:

    - **name**: Required string
    - **owner_tier_id**: Required integer id for related owner tier
    """
    new_owner = Owner(**owner_input.model_dump())
    session.add(new_owner)
    session.commit()
    session.refresh(new_owner)
    return new_owner


@router.patch("/{id}", response_model=OwnerDetailWriteOutput)
def update_owner(id: int, owner: OwnerInput, session: Session = Depends(get_session)):
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
    owner = session.get(Owner, id)
    if owner:
        session.delete(owner)
        session.commit()
    else:
        raise HTTPException(status_code=404)
