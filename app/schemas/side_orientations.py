import uuid

from typing import Optional
from pydantic import BaseModel, constr
from datetime import datetime


class SideOrientationInput(BaseModel):
    name: constr(max_length=5) | None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Right",
            }
        }


class SideOrientationUpdateInput(BaseModel):
    name: Optional[constr(max_length=5)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Right",
            }
        }


class SideOrientationBaseReadOutput(BaseModel):
    id: int
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Left",
            }
        }


class SideOrientationListOutput(SideOrientationBaseReadOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Left",
            }
        }


class SideOrientationDetailWriteOutput(BaseModel):
    id: int
    name: str
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Left",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


class SideOrientationDetailReadOutput(SideOrientationBaseReadOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Right",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
