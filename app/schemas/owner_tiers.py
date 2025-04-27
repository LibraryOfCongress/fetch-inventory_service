from typing import Optional

from pydantic import BaseModel, conint
from datetime import datetime, timezone


class OwnerTierInput(BaseModel):
    level: int
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "level": 1,
                "name": "organization"
            }
        }


class OwnerTierUpdateInput(BaseModel):
    level: Optional[int] = None
    name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "level": 1,
                "name": "organization"
            }
        }


class OwnerTierBaseOutput(BaseModel):
    id: int
    level: int
    name: str


class OwnerTierListOutput(OwnerTierBaseOutput):
    id: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "level": 2,
                "name": "division"
            }
        }


class OwnerTierDetailOutput(OwnerTierBaseOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "level": 1,
                "name": "organization",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
