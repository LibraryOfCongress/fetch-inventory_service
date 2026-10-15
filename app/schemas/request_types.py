from typing import Optional, List
from pydantic import BaseModel, conint, ConfigDict
from datetime import datetime, timezone


class RequestTypeInput(BaseModel):
    type: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "General Delivery"
            }
        }
    )


class RequestTypeUpdateInput(BaseModel):
    type: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "General Delivery"
            }
        }
    )


class RequestTypeBaseOutput(BaseModel):
    id: int
    type: str


class RequestTypeListOutput(RequestTypeBaseOutput):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "type": "General Delivery"
            }
        }
    )


class RequestTypeDetailWriteOutput(RequestTypeBaseOutput):
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "type": "General Delivery",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
    )


class RequestTypeDetailReadOutput(RequestTypeDetailWriteOutput):

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "type": "General Delivery",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
    )
