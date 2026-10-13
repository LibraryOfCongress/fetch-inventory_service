# /code/app/routers/owner_tiers.py - REFACRORED TO SQLALCHEMY V2

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from typing import Optional

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.owner_tiers import OwnerTier
from app.schemas.owner_tiers import (
    OwnerTierInput,
    OwnerTierUpdateInput,
    OwnerTierListOutput,
    OwnerTierDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/owners",
    tags=["owners"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/tiers", response_model=Page[OwnerTierListOutput])
def get_owner_tier_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get the list of owner tiers.
    """
    # Create a query to select all Owner Tier
    query = select(OwnerTier)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(OwnerTier)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/tiers/{id}", response_model=OwnerTierDetailOutput)
def get_owner_tier_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of an owner tier by its ID.
    """
    owner_tier = session.get(OwnerTier, id)
    if owner_tier:
        return owner_tier

    raise NotFound(detail=f"Owner Tier ID {id} Not Found")


@router.post("/tiers", response_model=OwnerTierDetailOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def create_owner_tier(
    owner_tier_input: OwnerTierInput, session: Session = Depends(get_session)
) -> OwnerTier:
    """
    Create an owner tier:
    """
    try:
        new_owner_tier = OwnerTier(**owner_tier_input.model_dump())
        session.add(new_owner_tier)
        session.commit()
        session.refresh(new_owner_tier)

        return new_owner_tier

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/tiers/{id}", response_model=OwnerTierDetailOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def update_owner_tier(
    id: int, owner_tier: OwnerTierUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an owner tier by its ID.
    """
    try:
        existing_owner_tier = session.get(OwnerTier, id)

        if existing_owner_tier is None:
            raise NotFound(detail=f"Owner Tier ID {id} Not Found")

        mutated_data = owner_tier.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_owner_tier, key, value)

        setattr(existing_owner_tier, "update_dt", datetime.now(timezone.utc))
        session.add(existing_owner_tier)
        session.commit()
        session.refresh(existing_owner_tier)

        return existing_owner_tier

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/tiers/{id}", dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def delete_owner_tier(id: int, session: Session = Depends(get_session)):
    """
    Delete an owner tier by its ID.
    """
    owner_tier = session.get(OwnerTier, id)

    if owner_tier:
        session.delete(owner_tier)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Owner Tier ID {id} Not Found")
