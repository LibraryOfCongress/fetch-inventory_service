# /code/app/routers/owners.py - REFACRORED TO SQLALCHEMY V2

from typing import Optional, Union

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.owners import Owner
from app.models.owner_tiers import OwnerTier
from app.schemas.owners import (
    OwnerInput,
    OwnerUpdateInput,
    OwnerListOutput,
    OwnerDetailWriteOutput,
    OwnerDetailReadOutput,
)
from app.config.exceptions import (
    BadRequest,
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


@router.get("/", response_model=Page[OwnerListOutput])
def get_owner_list(
    session: Session = Depends(get_session),
    owner_tier_id: Optional[int] = Query(None),
    parent_owner_id: Optional[Union[int, str]] = Query(None),
    parent_owner: Optional[str] = Query(None),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Owner name"),
) -> list:
    """
    Get a list of owners.
    """
    # Create a query to select all Owner
    query = select(Owner)

    if search:
        query = query.where(Owner.name.icontains(search))

    if owner_tier_id:
        query = query.where(Owner.owner_tier_id == owner_tier_id)

    # Handle parent_owner_id being explicitly "null"
    if parent_owner_id == "null":
        query = query.where(Owner.parent_owner_id.is_(None))
    elif parent_owner_id is not None:
        query = query.where(Owner.parent_owner_id == int(parent_owner_id))
        
    if parent_owner is not None:
        # V2 FIX: Use scalar_subquery() for subquery in WHERE clause
        parent_owner_subquery = select(Owner.id).where(Owner.name == parent_owner).scalar_subquery()
        query = query.where(Owner.parent_owner_id == parent_owner_subquery)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(Owner)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=OwnerDetailReadOutput)
def get_owner_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve owner details by ID.
    """
    owner = session.get(Owner, id)
    if owner:
        return owner

    raise NotFound(detail=f"Owner ID {id} Not Found")


@router.post("/", response_model=OwnerDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def create_owner(
    owner_input: OwnerInput, session: Session = Depends(get_session)
) -> Owner:
    """
    Create an owner:
    """
    try:
        new_owner = Owner(**owner_input.model_dump())

        # Check if the parent_owner_id is set
        if new_owner.parent_owner_id is not None:
            # Retrieve the parent owner
            # CRITICAL V2 FIX: session.exec().first() -> session.execute(query).scalars().first()
            parent_owner = session.execute(
                select(Owner).where(Owner.id == new_owner.parent_owner_id)
            ).scalars().first()
            if parent_owner is None:
                raise NotFound(detail=f"Owner ID {id} Not Found")

            # query new_owner.owner_tier to get proposed tier level
            # CRITICAL V2 FIX: session.exec().first() -> session.execute(query).scalars().first()
            new_owner_tier_level = (
                session.execute(
                    select(OwnerTier).where(OwnerTier.id == new_owner.owner_tier_id)
                )
                .scalars()
                .first()
                .level
            )

            # Check if the owner_tier is greater than the parent's owner_tier
            if new_owner_tier_level <= parent_owner.owner_tier.level:
                raise BadRequest(
                    detail="Owner tier must be lower level (higher value) than parent owner's tier"
                )

        # Add the new owner to the database
        session.add(new_owner)
        session.commit()
        session.refresh(new_owner)
        return new_owner

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=OwnerDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def update_owner(
    id: int, owner: OwnerUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an existing owner.
    """
    try:
        existing_owner = session.get(Owner, id)

        if existing_owner is None:
            raise NotFound(detail=f"Owner ID {id} Not Found")

        mutated_data = owner.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_owner, key, value)

        # Check if the parent_owner_id is set
        if existing_owner.parent_owner_id is not None:
            # Retrieve the parent owner
            # CRITICAL V2 FIX: session.exec().first() -> session.execute(query).scalars().first()
            parent_owner = session.execute(
                select(Owner).where(Owner.id == existing_owner.parent_owner_id)
            ).scalars().first()
            if parent_owner is None:
                raise NotFound(detail="Parent Owner Not Found")

            # Check if the owner_tier is greater than the parent's owner_tier
            if existing_owner.owner_tier.level <= parent_owner.owner_tier.level:
                raise BadRequest(
                    detail="Owner tier must be lower level (higher value) than parent owner's tier"
                )

        setattr(existing_owner, "update_dt", datetime.now(timezone.utc))
        session.add(existing_owner)
        session.commit()
        session.refresh(existing_owner)

        return existing_owner

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def delete_owner(id: int, session: Session = Depends(get_session)):
    """
    Delete an owner by their ID.
    """
    owner = session.get(Owner, id)

    if owner:
        session.delete(owner)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Owner ID {id} Not Found")


# --- Owner-DeliveryLocation Association Endpoints ---


@router.get("/{id}/delivery-locations", response_model=list)
def get_owner_delivery_locations(id: int, session: Session = Depends(get_session)):
    """
    Get all delivery locations associated with an owner.
    """
    from app.models.owner_delivery_locations import OwnerDeliveryLocation
    from app.models.delivery_locations import DeliveryLocation
    
    owner = session.get(Owner, id)
    if not owner:
        raise NotFound(detail=f"Owner ID {id} Not Found")
    
    # Query delivery locations for this owner
    locations = session.execute(
        select(DeliveryLocation)
        .join(OwnerDeliveryLocation)
        .where(OwnerDeliveryLocation.owner_id == id)
    ).scalars().all()
    
    return [{"id": loc.id, "name": loc.name, "address": loc.address} for loc in locations]


@router.post("/{id}/delivery-locations", status_code=201, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def add_owner_delivery_location(
    id: int,
    delivery_location_id: int,
    session: Session = Depends(get_session)
):
    """
    Add a delivery location to an owner's allowed locations.
    """
    from app.models.owner_delivery_locations import OwnerDeliveryLocation
    from app.models.delivery_locations import DeliveryLocation
    
    owner = session.get(Owner, id)
    if not owner:
        raise NotFound(detail=f"Owner ID {id} Not Found")
    
    delivery_location = session.get(DeliveryLocation, delivery_location_id)
    if not delivery_location:
        raise NotFound(detail=f"Delivery Location ID {delivery_location_id} Not Found")
    
    # Check if association already exists
    existing = session.execute(
        select(OwnerDeliveryLocation).where(
            OwnerDeliveryLocation.owner_id == id,
            OwnerDeliveryLocation.delivery_location_id == delivery_location_id
        )
    ).scalars().first()
    
    if existing:
        raise ValidationException(detail="This delivery location is already associated with this owner")
    
    # Create association
    new_association = OwnerDeliveryLocation(
        owner_id=id,
        delivery_location_id=delivery_location_id
    )
    session.add(new_association)
    session.commit()
    session.refresh(new_association)
    
    return {"id": new_association.id, "owner_id": id, "delivery_location_id": delivery_location_id}


@router.delete("/{id}/delivery-locations/{delivery_location_id}", dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def remove_owner_delivery_location(
    id: int,
    delivery_location_id: int,
    session: Session = Depends(get_session)
):
    """
    Remove a delivery location from an owner's allowed locations.
    """
    from app.models.owner_delivery_locations import OwnerDeliveryLocation
    
    association = session.execute(
        select(OwnerDeliveryLocation).where(
            OwnerDeliveryLocation.owner_id == id,
            OwnerDeliveryLocation.delivery_location_id == delivery_location_id
        )
    ).scalars().first()
    
    if not association:
        raise NotFound(detail="Association not found")
    
    session.delete(association)
    session.commit()
    
    return {"detail": "Delivery location removed from owner"}

