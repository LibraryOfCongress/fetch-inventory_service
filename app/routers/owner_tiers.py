from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.owner_tiers import OwnerTier
from app.schemas.owner_tiers import (
    OwnerTierInput,
    OwnerTierListOutput,
    OwnerTierDetailOutput,
)


router = APIRouter(
    prefix="/owners",
    tags=["owners"],
)


@router.get("/tiers", response_model=Page[OwnerTierListOutput])
def get_owner_tier_list(session: Session = Depends(get_session)) -> list:
    return paginate(session, select(OwnerTier))


@router.get("/tiers/{id}", response_model=OwnerTierDetailOutput)
def get_owner_tier_detail(id: int, session: Session = Depends(get_session)):
    owner_tier = session.get(OwnerTier, id)
    if owner_tier:
        return owner_tier
    else:
        raise HTTPException(status_code=404)


@router.post("/tiers", response_model=OwnerTierDetailOutput)
def create_owner_tier(owner_tier_input: OwnerTierInput, session: Session = Depends(get_session)) -> OwnerTier:
    """
    Create a owner tier:

    - **level**: Required unique integer that represents a tier
    - **name**: Required unique string that names a tier (category)
    """
    try:
        new_owner_tier = OwnerTier(**owner_tier_input.model_dump())
        session.add(new_owner_tier)
        session.commit()
        session.refresh(new_owner_tier)
        return new_owner_tier
    except IntegrityError as e:
        raise HTTPException(status_code=422, detail=f"{e}")


@router.patch("/tiers/{id}", response_model=OwnerTierDetailOutput)
def update_owner_tier(id: int, owner_tier: OwnerTierInput, session: Session = Depends(get_session)):
    try:
        existing_owner_tier = session.get(OwnerTier, id)
        if not existing_owner_tier:
            raise HTTPException(status_code=404)
        mutated_data = owner_tier.model_dump(exclude_unset=True)
        for key, value in mutated_data.items():
            setattr(existing_owner_tier, key, value)
        setattr(existing_owner_tier, "update_dt", datetime.utcnow())
        session.add(existing_owner_tier)
        session.commit()
        session.refresh(existing_owner_tier)
        return existing_owner_tier
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/tiers/{id}", status_code=204)
def delete_owner_tier(id: int, session: Session = Depends(get_session)):
    owner_tier = session.get(OwnerTier, id)
    if owner_tier:
        session.delete(owner_tier)
        session.commit()
    else:
        raise HTTPException(status_code=404)
