from typing import Optional
from pydantic import BaseModel, constr, condecimal
from datetime import datetime
from app.schemas.owners import OwnerDetailReadOutput


class SizeClassInput(BaseModel):
    name: Optional[constr(max_length=50)] = None
    short_name: Optional[constr(max_length=10)] = None
    assigned: Optional[bool] = None
    owner_ids: Optional[list[int]] = None
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "C-Low",
                "short_name": "CL",
                "assigned": False,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "owner_ids": [1, 2]
            }
        }


class SizeClassUpdateInput(SizeClassInput):

    class Config:
        json_schema_extra = {
            "example": {
                "name": "C-Low",
                "short_name": "CL",
                "assigned": False,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "owner_ids": [1, 2]
            }
        }


class SizeClassOwnerRemovalInput(BaseModel):
    owner_ids: list[int]

    class Config:
        json_schema_extra = {
            "example": {
                "owner_ids": [1, 2]
            }
        }

class SizeClassBaseOutput(BaseModel):
    id: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1
            }
        }


class SizeClassListOutput(SizeClassBaseOutput):
    name: str
    short_name: str
    assigned: bool
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None
    owners: Optional[list] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low",
                "short_name": "CL",
                "assigned": False,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "owners": [
                    {
                        "id": 1,
                        "name": "Special Collection Directorate",
                        "owner_tier_id": 2,
                        "parent_owner_id": 2,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                ]
            }
        }


class SizeClassDetailWriteOutput(SizeClassBaseOutput):
    name: str
    short_name: str
    assigned: Optional[bool] = None
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None
    owners: Optional[list] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low",
                "short_name": "CL",
                "assigned": False,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "owners": [
                    {
                        "id": 1,
                        "name": "Special Collection Directorate",
                        "owner_tier_id": 2,
                        "parent_owner_id": 2,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


class SizeClassDetailReadOutput(SizeClassDetailWriteOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low",
                "short_name": "CL",
                "assigned": False,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
