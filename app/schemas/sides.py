import uuid

from typing import Optional
from pydantic import BaseModel, constr
from datetime import datetime

from app.schemas.aisles import AisleBaseReadOutput
from app.schemas.modules import ModuleCustomDetailReadOutput
from app.schemas.buildings import BuildingBaseOutput
from app.schemas.side_orientations import SideOrientationBaseReadOutput


class SideInput(BaseModel):
    aisle_id: int
    side_orientation_id: int
    barcode: Optional[uuid.UUID]

    class Config:
        json_schema_extra = {
            "example": {
                "aisle_id": 1,
                "side_orientation_id": 1,
                "barcode": "550e8400-e29b-41d4-a716-446655440002"
            }
        }


class SideBaseOutput(BaseModel):
    id: int


class SideListOutput(SideBaseOutput):
    side_orientation_id: int
    aisle_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "aisle_id": 1,
                "side_orientation_id": 1
            }
        }


class SideDetailWriteOutput(SideBaseOutput):
    aisle_id: int
    side_orientation_id: int
    barcode_id: uuid.UUID | None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "aisle_id": 1,
                "side_orientation_id": 1,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440000",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class SideDetailReadOutput(SideBaseOutput):
    side_orientation: SideOrientationBaseReadOutput
    barcode: uuid.UUID | None
    create_dt: datetime
    update_dt: datetime
    building: BuildingBaseOutput
    module: ModuleCustomDetailReadOutput
    aisle: AisleBaseReadOutput


    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "side_orientation": {
                    "id": 1,
                    "name": "Left",
                },
                "barcode_id": "550e8400-e29b-41d4-a716-446655440000",
                "aisle": {
                    "id": 1,
                    "number": 1,
                },
                "building": {
                    "id": 1,
                    "name": "Southpoint Circle",
                },
                "module": {
                    "id": 1,
                    "module_number": {
                        "id": 1,
                        "number": 1,
                    },
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
