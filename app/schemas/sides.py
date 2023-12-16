import uuid

from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.schemas.aisles import AisleBaseReadOutput
from app.schemas.side_orientations import SideOrientationBaseReadOutput


class SideInput(BaseModel):
    aisle_id: int
    side_orientation_id: int

    class Config:
        json_schema_extra = {"example": {"aisle_id": 1, "side_orientation_id": 1}}


class SideUpdateInput(BaseModel):
    aisle_id: Optional[int] = None
    side_orientation_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "aisle_id": 1,
                "side_orientation_id": 1
            }
        }


class SideBaseOutput(BaseModel):
    id: int


class SideListOutput(SideBaseOutput):
    side_orientation_id: int
    aisle_id: int

    class Config:
        json_schema_extra = {
            "example": {"id": 1, "aisle_id": 1, "side_orientation_id": 1}
        }


class SideDetailWriteOutput(SideBaseOutput):
    aisle_id: int
    side_orientation_id: int
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "aisle_id": 1,
                "side_orientation_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


class SideDetailReadOutput(SideBaseOutput):
    side_orientation: SideOrientationBaseReadOutput
    create_dt: datetime
    update_dt: datetime
    aisle: AisleBaseReadOutput
    ladders: list

    class Config:
        json_schema_extra = {
            "example": {
                "id": 3,
                "side_orientation": {
                    "id": 1,
                    "name": "Left",
                },
                "aisle": {
                    "id": 1,
                    "number": 1,
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "ladders": [
                    {
                        "id": 1,
                        "ladder_number_id": 1,
                        "create_dt": "2023-11-05T21:04:07.718796",
                        "update_dt": "2023-11-05T21:04:07.718821",
                        "side_id": 3,
                    },
                    {
                        "id": 4,
                        "ladder_number_id": 2,
                        "create_dt": "2023-11-05T21:30:37.842984",
                        "update_dt": "2023-11-05T21:30:37.843005",
                        "side_id": 3,
                    },
                ],
            }
        }
