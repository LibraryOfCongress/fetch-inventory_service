from typing import Optional, List
from pydantic import BaseModel, conint, ConfigDict
from datetime import datetime, timezone


class PriorityInput(BaseModel):
    value: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "value": "High"
            }
        }
    )


class PriorityUpdateInput(BaseModel):
    value: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "value": "High"
            }
        }
    )


class PriorityBaseOutput(BaseModel):
    id: int
    value: str


class PriorityListOutput(PriorityBaseOutput):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "value": "High"
            }
        }
    )


class PriorityDetailWriteOutput(PriorityBaseOutput):
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "value": "High",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
    )


class PriorityDetailReadOutput(PriorityDetailWriteOutput):

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "value": "High",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
    )
