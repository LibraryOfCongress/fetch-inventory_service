import uuid

from typing import Optional
from pydantic import BaseModel, constr
from datetime import datetime


class BuildingInput(BaseModel):
    name: constr(max_length=25, strict=False) = None
    barcode: Optional[uuid.UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Southpoint Circle",
                "barcode": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class BuildingListOutput(BaseModel):
    id: int
    name: str | None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Southpoint Circle",
            }
        }


class BuildingDetailWriteOutput(BaseModel):
    id: int
    name: str | None
    barcode: uuid.UUID | None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Southpoint Circle",
                "barcode": "550e8400-e29b-41d4-a716-446655440000",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class BuildingDetailReadOutput(BaseModel):
    id: int
    name: str | None
    barcode: uuid.UUID | None
    create_dt: datetime
    update_dt: datetime
    modules: list

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Southpoint Circle",
                "barcode": "550e8400-e29b-41d4-a716-446655440000",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "modules": [
                    {
                    "id": 1,
                    "building_id": 1,
                    "barcode": "550e8400-e29b-41d4-a716-446655440001",
                    "module_number_id": 1,
                    "update_dt": "2023-10-09T17:19:23.780752",
                    "create_dt": "2023-10-09T17:19:23.780771"
                    }
                ]
            }
        }