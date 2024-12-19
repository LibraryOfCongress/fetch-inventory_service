import uuid

from typing import Optional, List
from pydantic import BaseModel, conint
from datetime import datetime

from app.schemas.shelf_types import ShelfTypeDetailOutput
from app.schemas.sides import SideDetailWriteOutput
from app.schemas.ladder_numbers import LadderNumberDetailOutput
from app.schemas.barcodes import BarcodeDetailReadOutput


class LadderInput(BaseModel):
    side_id: conint(ge=0, le=2147483647)
    ladder_number_id: Optional[conint(ge=0, le=32767)] = None
    ladder_number: Optional[int] = None
    sort_priority: Optional[conint(ge=0, le=32767)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "side_id": 1,
                "ladder_number_id": 1,
                "ladder_number": None,
                "sort_priority": 1
            }
        }


class LadderUpdateInput(BaseModel):
    side_id: Optional[conint(ge=0, le=2147483647)] = None
    ladder_number_id: Optional[conint(ge=0, le=32767)] = None
    sort_priority: Optional[conint(ge=0, le=32767)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "side_id": 1,
                "ladder_number_id": 1,
                "sort_priority": 1
            }
        }


class LadderBaseOutput(BaseModel):
    id: int


class LadderListOutput(LadderBaseOutput):
    side_id: int
    ladder_number_id: int
    sort_priority: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "side_id": 1,
                "ladder_number_id": 1,
                "sort_priority": 1
            }
        }


class LadderDetailWriteOutput(LadderBaseOutput):
    side_id: int
    ladder_number_id: int
    sort_priority: Optional[int] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "side_id": 1,
                "ladder_number_id": 1,
                "sort_priority": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class OwnerNestedForLadderOutput(BaseModel):
    id: int
    name: str


class ShelfNumberNestedForLadderOutput(BaseModel):
    number: int


class ContainerTypeNestedForLadderOutput(BaseModel):
    id: int
    type: str


class ShelvesNestedForLadderOutput(BaseModel):
    id: int
    available_space: Optional[int] = None
    sort_priority: Optional[int] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    shelf_number: ShelfNumberNestedForLadderOutput
    owner: OwnerNestedForLadderOutput
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    shelf_type: ShelfTypeDetailOutput
    container_type: Optional[ContainerTypeNestedForLadderOutput] = None
    create_dt: Optional[datetime] = None
    update_dt: Optional[datetime] = None


class SideNestedForLadderOutput(SideDetailWriteOutput):
    sort_priority: Optional[int] = None


class LadderDetailReadOutput(LadderBaseOutput):
    sort_priority: Optional[int] = None
    side: SideDetailWriteOutput
    ladder_number: LadderNumberDetailOutput
    shelves: List[ShelvesNestedForLadderOutput]
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "sort_priority": 1,
                "side": {
                    "id": 1,
                    "sort_priority": 1,
                    "aisle_id": 1,
                    "side_orientation_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "ladder_number": {
                    "id": 1,
                    "number": 1,
                    "create_dt": "2023-10-09T17:04:09.812257",
                    "update_dt": "2023-10-10T01:00:28.576069"
                },
                "shelves": [
                    {
                        "id": 1,
                        "available_space": 30,
                        "shelf_number": {
                            "number": 3
                        },
                        "shelf_type": {
                            "id": 1,
                            "type": "Long",
                            "size_class_id": 1,
                            "size_class": {
                                "id": 1,
                                "name": "C-Low",
                                "short_name": "CL"
                            },
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398",
                        },
                        "owner": {
                            "id": 1,
                            "name": "Library Of Congress"
                        },
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "size_class_id": 1
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
