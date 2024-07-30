from typing import Optional, List
from pydantic import BaseModel, conint
from datetime import datetime


class DeliveryLocationInput(BaseModel):
    name: Optional[str] = None
    address: str

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Example Recipient",
                "address": "123 Example St, Example City, State Zip Code"
            }
        }


class DeliveryLocationUpdateInput(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Example Recipient",
                "address": "123 Example St, Example City, State Zip Code"
            }
        }


class DeliveryLocationBaseOutput(BaseModel):
    id: int
    name: Optional[str] = None
    address: str


class DeliveryLocationListOutput(DeliveryLocationBaseOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Example Recipient",
                "address": "123 Example St, Example City, State Zip Code"
            }
        }


class DeliveryLocationDetailWriteOutput(DeliveryLocationBaseOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Example Recipient",
                "address": "123 Example St, Example City, State Zip Code",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class DeliveryLocationDetailReadOutput(DeliveryLocationDetailWriteOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Example Recipient",
                "address": "123 Example St, Example City, State Zip Code",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
