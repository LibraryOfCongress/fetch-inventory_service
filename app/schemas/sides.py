import uuid

from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone

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


class LadderNumberNestedForSide(BaseModel):
    number: int


class LadderNestedForSide(BaseModel):
    id: int
    ladder_number: LadderNumberNestedForSide
    sort_priority: Optional[int] = None
    create_dt: datetime
    update_dt: datetime


class SideDetailReadOutput(SideBaseOutput):
    side_orientation: SideOrientationBaseReadOutput
    create_dt: datetime
    update_dt: datetime
    aisle: AisleBaseReadOutput
    ladders: List[LadderNestedForSide]

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
                        "ladder_number": {
                            "number": 1
                        },
                        "sort_priority": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                ]
            }
        }
