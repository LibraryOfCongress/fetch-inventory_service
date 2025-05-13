from typing import Optional, List
from pydantic import BaseModel, conint
from datetime import datetime, timezone


class PriorityInput(BaseModel):
    value: str

    class Config:
        json_schema_extra = {
            "example": {
                "value": "High"
            }
        }


class PriorityUpdateInput(BaseModel):
    value: str

    class Config:
        json_schema_extra = {
            "example": {
                "value": "High"
            }
        }


class PriorityBaseOutput(BaseModel):
    id: int
    value: str


class PriorityListOutput(PriorityBaseOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "value": "High"
            }
        }


class PriorityDetailWriteOutput(PriorityBaseOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "value": "High",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class PriorityDetailReadOutput(PriorityDetailWriteOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "value": "High",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
