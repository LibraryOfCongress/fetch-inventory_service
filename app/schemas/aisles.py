import uuid

from typing import Optional, List
from pydantic import BaseModel, conint
from datetime import datetime

from app.schemas.modules import ModuleCustomDetailReadOutput
from app.schemas.aisle_numbers import AisleNumberBaseOutput


class AisleInput(BaseModel):
    aisle_number_id: Optional[conint(ge=0, le=2147483647)] = None
    aisle_number: Optional[int] = None
    module_id: Optional[conint(ge=0, le=32767)] = None
    sort_priority: Optional[conint(ge=0, le=32767)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "aisle_number_id": 1,
                "aisle_number": None,
                "module_id": 1,
                "sort_priority": 1
            }
        }


class AisleUpdateInput(BaseModel):
    aisle_number_id: Optional[conint(ge=0, le=2147483647)] = None
    module_id: Optional[conint(ge=0, le=32767)] = None
    sort_priority: Optional[conint(ge=0, le=32767)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "aisle_number_id": 1,
                "module_id": 1,
                "sort_priority": 1
            }
        }


class AisleBaseReadOutput(BaseModel):
    id: int
    aisle_number_id: int


class AisleListOutput(AisleBaseReadOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "aisle_number_id": 1
            }
        }


class AisleDetailWriteOutput(BaseModel):
    id: int
    aisle_number_id: int
    module_id: int | None = None
    sort_priority: Optional[int] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "aisle_number_id": 1,
                "module_id": 1,
                "sort_priority": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


class SideOrientationNestedForAisle(BaseModel):
    name: str


class SideNestedForAisle(BaseModel):
    id: int
    side_orientation: SideOrientationNestedForAisle


class AisleDetailReadOutput(BaseModel):
    id: int
    sort_priority: Optional[int] = None
    create_dt: datetime
    update_dt: datetime
    module: ModuleCustomDetailReadOutput | None
    aisle_number: AisleNumberBaseOutput
    sides: List[SideNestedForAisle]

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "number": 1,
                "sort_priority": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "module": {
                    "id": 1,
                    "module_number": "1",
                },
                "aisle_number": {
                    "id": 1,
                    "number": 1
                },
                "sides": [
                    {
                        "id": 1,
                        "side_orientation": {
                            "name": "Left"
                        }
                    }
                ]
            }
        }
