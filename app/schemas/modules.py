import uuid

from typing import Optional
from pydantic import BaseModel, conint
from datetime import datetime

from app.schemas.buildings import BuildingDetailWriteOutput
from app.schemas.module_numbers import ModuleNumberDetailOutput


class ModuleInput(BaseModel):
    building_id: conint(ge=0, le=32767)
    module_number_id: conint(ge=0, le=32767)
    barcode: Optional[uuid.UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "building_id": 1,
                "module_number_id": 1,
                "barcode": "550e8400-e29b-41d4-a716-446655440001"
            }
        }


class ModuleListOutput(BaseModel):
    id: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
            }
        }


class ModuleDetailWriteOutput(BaseModel):
    id: int
    building_id: int
    module_number_id: int
    barcode: uuid.UUID | None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "building_id": 1,
                "module_number_id": 1,
                "barcode": "550e8400-e29b-41d4-a716-446655440001",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class ModuleDetailReadOutput(BaseModel):
    id: int
    building: BuildingDetailWriteOutput
    module_number: ModuleNumberDetailOutput
    barcode: uuid.UUID | None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "building": {
                    "id": 1,
                    "name": "Southpoint Triangle",
                    "barcode": "550e8400-e29b-41d4-a716-446655440000",
                    "create_dt": "2023-10-09T05:51:20.254535",
                    "update_dt": "2023-10-09T06:16:13.653205"
                },
                "module_number": {
                    "id": 1,
                    "number": 1,
                    "create_dt": "2023-10-09T17:04:09.812257",
                    "update_dt": "2023-10-10T01:00:28.576069"
                },
                "barcode": "550e8400-e29b-41d4-a716-446655440001",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
