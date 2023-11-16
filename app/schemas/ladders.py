import uuid

from typing import Optional
from pydantic import BaseModel, conint
from datetime import datetime

from app.schemas.sides import SideDetailWriteOutput
from app.schemas.ladder_numbers import LadderNumberDetailOutput


class LadderInput(BaseModel):
    side_id: conint(ge=0, le=2147483647)
    ladder_number_id: conint(ge=0, le=32767)

    class Config:
        json_schema_extra = {
            "example": {
                "side_id": 1,
                "ladder_number_id": 1
            }
        }


class LadderBaseOutput(BaseModel):
    id: int


class LadderListOutput(LadderBaseOutput):
    side_id: int
    ladder_number_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "side_id": 1,
                "ladder_number_id": 1
            }
        }


class LadderDetailWriteOutput(LadderBaseOutput):
    side_id: int
    ladder_number_id: int
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "side_id": 1,
                "ladder_number_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class LadderDetailReadOutput(LadderBaseOutput):
    side: SideDetailWriteOutput
    ladder_number: LadderNumberDetailOutput
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "side": {
                    "id": 1,
                    "aisle_id": 1,
                    "side_orientation_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "ladder_number": {
                    "id": 1,
                    "number": 1,
                    "create_dt": "2023-10-09T17:04:09.812257",
                    "update_dt": "2023-10-10T01:00:28.576069"
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
