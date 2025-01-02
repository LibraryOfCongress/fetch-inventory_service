from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
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
from app.utilities import get_sorted_query

router = APIRouter(
    prefix="/requests",
    tags=["requests"],
)


@router.get("/locations", response_model=Page[DeliveryLocationListOutput])
def get_delivery_location_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a list of delivery locations

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.

     **Returns:**
    - Delivery Location List Output: A paginated list of Delivery Location.
    """

    # Create a query to retrieve all Delivery Location
    query = select(DeliveryLocation).distinct()

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(DeliveryLocation, query, sort_params)

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


@router.post("/locations", response_model=DeliveryLocationDetailWriteOutput, status_code=201)
def create_delivery_location(
    delivery_location_input: DeliveryLocationInput, session: Session = Depends(get_session)
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


@router.patch("/locations/{id}", response_model=DeliveryLocationDetailWriteOutput)
def update_delivery_location(
    id: int, delivery_location: DeliveryLocationUpdateInput, session: Session = Depends(get_session)
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

        setattr(existing_delivery_location, "update_dt", datetime.utcnow())
        session.add(existing_delivery_location)
        session.commit()
        session.refresh(existing_delivery_location)

        return existing_delivery_location

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/locations/{id}")
def delete_delivery_location(id: int, session: Session = Depends(get_session)):
    """
    Delete an Request Type by ID
    """
    delivery_location = session.get(DeliveryLocation, id)

    if delivery_location:
        session.delete(delivery_location)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Request Type ID {id} Deleted "
                                    f"Successfully"
        )

    raise NotFound(detail=f"Request Type ID {id} Not Found")
