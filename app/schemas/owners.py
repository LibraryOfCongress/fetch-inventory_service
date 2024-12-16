import uuid

from typing import Optional, List
from pydantic import BaseModel, conint
from datetime import datetime

from app.schemas.owner_tiers import OwnerTierDetailOutput


class OwnerInput(BaseModel):
    name: str
    owner_tier_id: int
    parent_owner_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Special Collection Directorate",
                "owner_tier_id": 2,
                "parent_owner_id": None,
            }
        }


class OwnerUpdateInput(BaseModel):
    name: Optional[str] = None
    owner_tier_id: Optional[int] = None
    parent_owner_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Special Collection Directorate",
                "owner_tier_id": 2,
                "parent_owner_id": 2,
            }
        }


class OwnerBaseOutput(BaseModel):
    id: int
    name: str
    owner_tier_id: int
    parent_owner_id: Optional[int] = None
    size_classes: Optional[list] = None


class NestedOwnerTierDetailOutput(BaseModel):
    id: int
    level: int
    name: str


class NestedParentOwnerDetailReadOutput(BaseModel):
    id: int
    name: str


class OwnerListOutput(OwnerBaseOutput):
    parent_owner: Optional[NestedParentOwnerDetailReadOutput] = None
    owner_tier: Optional[NestedOwnerTierDetailOutput] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Special Collection Directorate",
                "owner_tier_id": 2,
                "owner_tier": {
                    "id": 1,
                    "level": 1,
                    "name": "organization"
                },
                "parent_owner_id": 2,
                "parent_owner": {
                    "id": 2,
                    "name": "Library of Congress"
                },
                "size_classes": [
                    {
                        "id": 1,
                        "name": "C-Low",
                        "short_name": "CL",
                        "height": 15.7,
                        "width": 30.33,
                        "depth": 27
                    }
                ]
            }
        }


class OwnerDetailWriteOutput(OwnerBaseOutput):
    owner_tier: Optional[OwnerTierDetailOutput] = None
    parent_owner: Optional[NestedParentOwnerDetailReadOutput] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Special Collection Directorate",
                "owner_tier_id": 2,
                "owner_tier": {
                    "id": 1,
                    "level": 1,
                    "name": "organization"
                },
                "parent_owner_id": 2,
                "parent_owner": {
                    "id": 2,
                    "name": "Library of Congress"
                },
                "size_classes": [
                    {
                        "id": 1,
                        "name": "C-Low",
                        "short_name": "CL",
                        "height": 15.7,
                        "width": 30.33,
                        "depth": 27
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class OwnerDetailReadOutput(OwnerBaseOutput):
    owner_tier: OwnerTierDetailOutput
    parent_owner: Optional["OwnerDetailReadOutput"] = None
    children: List["OwnerBaseOutput"] = []
    create_dt: datetime
    update_dt: datetime
    # TODO serialize shelf list without recursion (don't reuse this class)

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Special Collection Directorate",
                "owner_tier_id": 2,
                "parent_owner_id": 2,
                "owner_tier": {
                    "id": 1,
                    "level": 2,
                    "name": "division",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "parent_owner": {
                    "id": 2,
                    "name": "Library of Congress",
                    "owner_tier_id": 1,
                    "parent_owner_id": None,
                    "owner_tier": {
                        "id": 2,
                        "level": 1,
                        "name": "organization",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "size_classes": [
                    {
                        "id": 1,
                        "name": "C-Low",
                        "short_name": "CL",
                        "height": 15.7,
                        "width": 30.33,
                        "depth": 27
                    }
                ],
                "children": [],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
