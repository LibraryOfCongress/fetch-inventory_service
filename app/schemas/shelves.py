import uuid

from typing import Optional, List
from pydantic import BaseModel, conint, condecimal
from datetime import datetime

from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.ladders import LadderDetailWriteOutput
from app.schemas.shelf_numbers import ShelfNumberDetailOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput
from app.schemas.barcodes import BarcodeDetailReadOutput


class ShelfInput(BaseModel):
    sort_priority: Optional[conint(ge=0, le=32767)] = None
    ladder_id: conint(ge=0, le=2147483647)
    container_type_id: conint(ge=0, le=2147483647)
    shelf_type_id: conint(ge=0, le=2147483647)
    shelf_number_id: Optional[conint(ge=0, le=32767)] = None
    shelf_number: Optional[int] = None
    owner_id: conint(ge=0, le=32767)
    height: condecimal(decimal_places=2)
    width: condecimal(decimal_places=2)
    depth: condecimal(decimal_places=2)
    barcode_id: uuid.UUID | None

    class Config:
        json_schema_extra = {
            "example": {
                "sort_priority": 1,
                "ladder_id": 1,
                "container_type_id": 1,
                "shelf_number_id": 1,
                "shelf_number": None,
                "shelf_type_id": 1,
                "owner_id": 1,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
            }
        }


class ShelfUpdateInput(BaseModel):
    sort_priority: Optional[conint(ge=0, le=32767)] = None
    ladder_id: Optional[conint(ge=0, le=2147483647)] = None
    container_type_id: Optional[conint(ge=0, le=2147483647)] = None
    shelf_type_id: Optional[conint(ge=0, le=2147483647)] = None
    shelf_number_id: Optional[conint(ge=0, le=32767)] = None
    owner_id: Optional[conint(ge=0, le=32767)] = None
    available_space: Optional[conint(ge=0, le=32767)] = None
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None
    barcode_id: Optional[uuid.UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "sort_priority": 1,
                "ladder_id": 1,
                "container_type_id": 1,
                "shelf_type_id": 1,
                "shelf_number_id": 1,
                "owner_id": 1,
                "available_space": 33,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }


class NestedSizeClassDetailOutput(BaseModel):
    id: int
    name: str
    short_name: str
    assigned: bool
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None
    create_dt: datetime
    update_dt: datetime


class NestedShelfTypeDetailOutput(BaseModel):
    id: int
    type: str
    size_class_id: int
    size_class: Optional[NestedSizeClassDetailOutput]
    max_capacity: int
    create_dt: datetime
    update_dt: datetime


class ShelfBaseOutput(BaseModel):
    id: int


class ShelfListOutput(ShelfBaseOutput):
    sort_priority: Optional[int] = None
    ladder_id: int
    container_type_id: Optional[int] = None
    shelf_type_id: int
    shelf_type: NestedShelfTypeDetailOutput
    owner_id: Optional[int] = None
    barcode: BarcodeDetailReadOutput

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "sort_priority": 1,
                "ladder_id": 1,
                "container_type_id": 1,
                "shelf_type_id": 1,
                "shelf_type": {
                    "id": 1,
                    "type": "Long",
                    "size_class_id": 1,
                    "size_class": {
                        "id": 1,
                        "name": "C-Low",
                        "short_name": "CL",
                        "assigned": False,
                        "height": 15.7,
                        "width": 30.33,
                        "depth": 27,
                        "create_dt": "2023-11-27T12:34:56.789123Z",
                        "update_dt": "2023-11-27T12:34:56.789123Z"
                    },
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "owner_id": 1,
                "barcode": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "value": "5901234123457",
                    "type_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                }
            }
        }


class ShelfDetailWriteOutput(ShelfBaseOutput):
    sort_priority: Optional[int] = None
    barcode_id: uuid.UUID
    ladder_id: int
    container_type_id: Optional[int] = None
    shelf_type_id: int
    shelf_number_id: int
    owner_id: Optional[int] = None
    available_space: int
    height: float
    width: float
    depth: float
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    shelf_type: NestedShelfTypeDetailOutput
    ladder: LadderDetailWriteOutput
    owner: Optional[OwnerDetailReadOutput] = None
    barcode: BarcodeDetailReadOutput
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "sort_priority": 1,
                "ladder_id": 1,
                "available_space": 33,
                "shelf_number_id": 1,
                "container_type_id": 1,
                "shelf_type_id": 1,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "container_type": {
                    "id": 1,
                    "type": "Tray",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "shelf_type": {
                    "id": 1,
                    "type": "Shelf",
                    "size_class_id": 1,
                    "size_class": {
                        "id": 1,
                        "name": "C-Low",
                        "short_name": "CL",
                        "assigned": False,
                        "height": 15.7,
                        "width": 30.33,
                        "depth": 27,
                        "create_dt": "2023-11-27T12:34:56.789123Z",
                        "update_dt": "2023-11-27T12:34:56.789123Z"
                    },
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "ladder": {
                    "id": 1,
                    "side_id": 1,
                    "ladder_number_id": 1,
                    "sort_priority": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "owner": {
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
                    "children": [],
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "barcode": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "value": "5901234123457",
                    "type_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


class ShelfPositionNumberNestedForShelf(BaseModel):
    number: int


class ShelfPositionNestedForShelf(BaseModel):
    id: int
    shelf_position_number: ShelfPositionNumberNestedForShelf


class ShelfDetailReadOutput(ShelfBaseOutput):
    sort_priority: Optional[int] = None
    ladder: LadderDetailWriteOutput
    shelf_number: ShelfNumberDetailOutput
    shelf_type_id: int
    shelf_type: NestedShelfTypeDetailOutput
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    owner: Optional[OwnerDetailReadOutput] = None
    available_space: int
    height: float
    width: float
    depth: float
    barcode_id: uuid.UUID
    barcode: BarcodeDetailReadOutput
    create_dt: datetime
    update_dt: datetime
    shelf_positions: List[ShelfPositionNestedForShelf]

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "sort_priority": 1,
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
                "shelf_type_id": 1,
                "shelf_type": {
                    "id": 1,
                    "type": "Long",
                    "size_class_id": 1,
                    "size_class": {
                        "id": 1,
                        "name": "C-Low",
                        "short_name": "CL",
                        "assigned": False,
                        "height": 15.7,
                        "width": 30.33,
                        "depth": 27,
                        "create_dt": "2023-11-27T12:34:56.789123Z",
                        "update_dt": "2023-11-27T12:34:56.789123Z"
                    },
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "container_type": {
                    "id": 1,
                    "type": "Tray",
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
                "available_space": 33,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "shelf_positions": [
                    {
                        "id": 278,
                        "shelf_position_number": {
                            "number": 1
                        }
                    }
                ]
            }
        }
