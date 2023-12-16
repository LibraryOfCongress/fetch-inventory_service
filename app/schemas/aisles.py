import uuid

from typing import Optional
from pydantic import BaseModel, constr, conint
from datetime import datetime

from app.schemas.modules import ModuleCustomDetailReadOutput
from app.schemas.buildings import BuildingBaseOutput
from app.schemas.aisle_numbers import AisleNumberBaseOutput


class AisleInput(BaseModel):
    aisle_number_id: conint(ge=0, le=2147483647)
    building_id: Optional[conint(ge=0, le=32767)] = None
    module_id: Optional[conint(ge=0, le=32767)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "aisle_number_id": 1,
                "building_id": 1,
                "module_id": 1
            }
        }


class AisleUpdateInput(BaseModel):
    aisle_number_id: Optional[conint(ge=0, le=2147483647)] = None
    building_id: Optional[conint(ge=0, le=32767)] = None
    module_id: Optional[conint(ge=0, le=32767)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "aisle_number_id": 1,
                "building_id": 1,
                "module_id": 1
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
    building_id: int | None = None
    module_id: int | None = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "aisle_number_id": 1,
                "building_id": 1,
                "module_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class AisleDetailReadOutput(BaseModel):
    id: int
    create_dt: datetime
    update_dt: datetime
    building: BuildingBaseOutput | None
    module: ModuleCustomDetailReadOutput | None
    aisle_number: AisleNumberBaseOutput

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "number": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "building": {
                    "id": 1,
                    "name": "Southpoint Circle"
                },
                "module": {
                    "id": 1,
                    "module_number": {
                        "id": 1,
                        "number": 1
                    },
                },
            }
        }
