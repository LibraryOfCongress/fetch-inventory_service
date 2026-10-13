# /code/app/schemas/owner_delivery_locations.py

from pydantic import BaseModel
from typing import Optional


class OwnerDeliveryLocationInput(BaseModel):
    """Input schema for creating owner-delivery location association."""
    delivery_location_id: int


class OwnerDeliveryLocationOutput(BaseModel):
    """Output schema for owner-delivery location association."""
    id: int
    owner_id: int
    delivery_location_id: int

    class Config:
        from_attributes = True


class DeliveryLocationForOwnerOutput(BaseModel):
    """Output schema for delivery location details when listing for an owner."""
    id: int
    name: Optional[str] = None
    address: str

    class Config:
        from_attributes = True
