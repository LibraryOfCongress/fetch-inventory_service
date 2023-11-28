import uuid

from typing import Optional
from pydantic import BaseModel, conint
from datetime import datetime

from app.schemas.owner_tiers import OwnerTierDetailOutput


class OwnerInput(BaseModel):
    name: str
    owner_tier_id: conint(ge=1, le=4)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Special Collection Directorate",
                "owner_tier_id": 2
            }
        }


class OwnerBaseOutput(BaseModel):
    id: int
    name: str
    owner_tier_id: int


class OwnerListOutput(OwnerBaseOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Special Collection Directorate",
                "owner_tier_id": 2
            }
        }


class OwnerDetailWriteOutput(OwnerBaseOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Special Collection Directorate",
                "owner_tier_id": 2,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class OwnerDetailReadOutput(OwnerBaseOutput):
    owner_tier: OwnerTierDetailOutput
    create_dt: datetime
    update_dt: datetime
    #TODO serialize shelf list without recursion (don't reuse this class)

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Special Collection Directorate",
                "owner_tier_id": 2,
                "owner_tier": {
                    "id": 1,
                    "level": 2,
                    "name": "division",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
