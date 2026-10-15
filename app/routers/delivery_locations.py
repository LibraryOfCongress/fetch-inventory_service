# /code/app/routers/delivery_locations.py - REFACRORED TO SQLALCHEMY V2

from typing import Optional

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
from app.models.delivery_locations import DeliveryLocation
from app.schemas.delivery_locations import (
    DeliveryLocationInput,
    DeliveryLocationUpdateInput,
    DeliveryLocationListOutput,
    DeliveryLocationDetailWriteOutput,
    DeliveryLocationDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/requests",
    tags=["requests"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/locations", response_model=Page[DeliveryLocationListOutput])
def get_delivery_location_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(
        None, description="Search by Request " "Delivery Locations Name"
    ),
    owner_id: Optional[int] = Query(None, description="Filter by owner ID"),
) -> list:
    """
    Get a list of delivery locations.
    Optionally filter by owner_id to get only locations allowed for that owner.
    """
    from app.models.owner_delivery_locations import OwnerDeliveryLocation

    # Create a query to retrieve all Delivery Location
    query = select(DeliveryLocation)

    if search:
        query = query.where(DeliveryLocation.name.icontains(search))
    
    # Filter by owner if specified
    if owner_id is not None:
        query = query.join(OwnerDeliveryLocation).where(
            OwnerDeliveryLocation.owner_id == owner_id
        )

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using RequestSorter
        sorter = BaseSorter(DeliveryLocation)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/locations/{id}", response_model=DeliveryLocationDetailReadOutput)
def get_delivery_location_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve delivery location details by ID
    """
    delivery_location = session.get(DeliveryLocation, id)
    if delivery_location:
        return delivery_location

    raise NotFound(detail=f"Request Type ID {id} Not Found")


@router.post(
    "/locations",
    response_model=DeliveryLocationDetailWriteOutput,
    status_code=201,
    dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))],
)
def create_delivery_location(
    delivery_location_input: DeliveryLocationInput,
    session: Session = Depends(get_session),
) -> DeliveryLocation:
    """
    Create a Request Type
    """
    try:
        new_delivery_location = DeliveryLocation(**delivery_location_input.model_dump())

        # Add the new delivery location to the database
        session.add(new_delivery_location)
        session.commit()
        session.refresh(new_delivery_location)
        return new_delivery_location

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/locations/{id}", response_model=DeliveryLocationDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def update_delivery_location(
    id: int,
    delivery_location: DeliveryLocationUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update an existing Request Type
    """
    try:
        existing_delivery_location = session.get(DeliveryLocation, id)

        if existing_delivery_location is None:
            raise NotFound(detail=f"Request Type ID {id} Not Found")

        mutated_data = delivery_location.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_delivery_location, key, value)

        setattr(existing_delivery_location, "update_dt", datetime.now(timezone.utc))
        session.add(existing_delivery_location)
        session.commit()
        session.refresh(existing_delivery_location)

        return existing_delivery_location

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/locations/{id}", dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def delete_delivery_location(id: int, session: Session = Depends(get_session)):
    """
    Delete an Request Type by ID
    """
    delivery_location = session.get(DeliveryLocation, id)

    if delivery_location:
        session.delete(delivery_location)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Request Type ID {id} Not Found")
