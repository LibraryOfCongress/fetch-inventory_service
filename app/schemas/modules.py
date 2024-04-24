import uuid

from typing import Optional, List
from pydantic import BaseModel, conint
from datetime import datetime

from app.schemas.buildings import BuildingDetailWriteOutput
from app.schemas.module_numbers import ModuleNumberBaseOutput, ModuleNumberDetailOutput


class ModuleInput(BaseModel):
    building_id: conint(ge=0, le=32767)
    module_number_id: conint(ge=0, le=32767)

    class Config:
        json_schema_extra = {
            "example": {
                "building_id": 1,
                "module_number_id": 1
            }
        }


class ModuleUpdateInput(BaseModel):
    building_id: Optional[int] = None
    module_number_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "building_id": 1,
                "module_number_id": 1
            }
        }


class ModuleBaseOutput(BaseModel):
    id: int


class ModuleListOutput(ModuleBaseOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1
            }
        }


class ModuleDetailWriteOutput(ModuleBaseOutput):
    building_id: int
    module_number_id: int
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "building_id": 1,
                "module_number_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class AisleNumberNestedForModule(BaseModel):
    number: int


class AisleNestedForModule(BaseModel):
    id: int
    aisle_number: AisleNumberNestedForModule


class ModuleDetailReadOutput(ModuleBaseOutput):
    building: BuildingDetailWriteOutput
    module_number: ModuleNumberDetailOutput
    aisles: List[AisleNestedForModule]
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "building": {
                    "id": 1,
                    "name": "Southpoint Triangle",
                    "create_dt": "2023-10-09T05:51:20.254535",
                    "update_dt": "2023-10-09T06:16:13.653205"
                },
                "module_number": {
                    "id": 1,
                    "number": 1,
                    "create_dt": "2023-10-09T17:04:09.812257",
                    "update_dt": "2023-10-10T01:00:28.576069"
                },
                "aisles": [
                    {
                        "id": 1,
                        "aisle_number": {
                            "number": 1
                        }
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class ModuleCustomDetailReadOutput(ModuleBaseOutput):
    module_number: ModuleNumberBaseOutput

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "module_number": {
                    "id": 1,
                    "number": 1
                },
            }
        }
