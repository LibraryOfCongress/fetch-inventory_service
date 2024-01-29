import uuid

from typing import Optional
from pydantic import BaseModel, conint, condecimal
from datetime import datetime

from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.ladders import LadderDetailWriteOutput
from app.schemas.shelf_numbers import ShelfNumberDetailOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput
from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.tray_size_class import TraySizeClassDetailReadOutput


class ShelfInput(BaseModel):
    ladder_id: conint(ge=0, le=2147483647)
    container_type_id: conint(ge=0, le=2147483647)
    tray_size_class_id: conint(ge=0, le=32767)
    shelf_number_id: conint(ge=0, le=32767)
    owner_id: conint(ge=0, le=32767)
    capacity: conint(ge=0, le=32767)
    height: condecimal(decimal_places=2)
    width: condecimal(decimal_places=2)
    depth: condecimal(decimal_places=2)
    barcode_id: uuid.UUID | None

    class Config:
        json_schema_extra = {
            "example": {
                "ladder_id": 1,
                "container_type_id": 1,
                "tray_size_class_id": 1,
                "shelf_number_id": 1,
                "owner_id": 1,
                "capacity": 33,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
            }
        }


class ShelfUpdateInput(BaseModel):
    ladder_id: Optional[conint(ge=0, le=2147483647)] = None
    container_type_id: Optional[conint(ge=0, le=2147483647)] = None
    tray_size_class_id: Optional[conint(ge=0, le=32767)] = None
    shelf_number_id: Optional[conint(ge=0, le=32767)] = None
    owner_id: Optional[conint(ge=0, le=32767)] = None
    capacity: Optional[conint(ge=0, le=32767)] = None
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None
    barcode_id: Optional[uuid.UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "ladder_id": 1,
                "container_type_id": 1,
                "tray_size_class_id":1,
                "shelf_number_id": 1,
                "owner_id": 1,
                "capacity": 33,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }


class ShelfBaseOutput(BaseModel):
    id: int


class ShelfListOutput(ShelfBaseOutput):
    ladder_id: int

    class Config:
        json_schema_extra = {"example": {"id": 1, "ladder_id": 1}}


class ShelfDetailWriteOutput(ShelfBaseOutput):
    ladder_id: int
    container_type_id: int
    tray_size_class_id: int
    shelf_number_id: int
    owner_id: int
    capacity: int
    height: float
    width: float
    depth: float
    barcode_id: uuid.UUID
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "ladder_id": 1,
                "capacity": 33,
                "shelf_number_id": 1,
                "container_type_id": 1,
                "tray_size_class_id": 1,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


class ShelfDetailReadOutput(ShelfBaseOutput):
    ladder: LadderDetailWriteOutput
    shelf_number: ShelfNumberDetailOutput
    container_type: ContainerTypeDetailReadOutput
    tray_size_class: TraySizeClassDetailReadOutput
    owner: OwnerDetailReadOutput
    capacity: int
    height: float
    width: float
    depth: float
    barcode_id: uuid.UUID
    barcode: BarcodeDetailReadOutput
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "ladder": {
                    "id": 1,
                    "side_id": 1,
                    "ladder_number_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "shelf_number": {
                    "id": 1,
                    "number": 1,
                    "create_dt": "2023-10-09T17:04:09.812257",
                    "update_dt": "2023-10-10T01:00:28.576069",
                },
                "container_type": {
                    "id": 1,
                    "type": "Tray",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "tray_size_class": {
                    "id": 1,
                    "name": "C-Low",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "owner": {
                    "id": 1,
                    "name": "Special Collection Directorate",
                    "owner_tier_id": 2,
                    "owner_tier": {
                        "id": 1,
                        "level": 2,
                        "name": "division",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398",
                    },
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "barcode": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "value": "5901234123457",
                    "type_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "capacity": 33,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
