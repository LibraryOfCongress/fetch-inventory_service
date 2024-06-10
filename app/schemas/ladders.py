import uuid

from typing import Optional, List
from pydantic import BaseModel, conint
from datetime import datetime

from app.schemas.sides import SideDetailWriteOutput
from app.schemas.ladder_numbers import LadderNumberDetailOutput
from app.schemas.barcodes import BarcodeDetailReadOutput


class LadderInput(BaseModel):
    side_id: conint(ge=0, le=2147483647)
    ladder_number_id: conint(ge=0, le=32767)
    sort_priority: Optional[conint(ge=0, le=32767)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "side_id": 1,
                "ladder_number_id": 1,
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
    sort_priority: int

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
    sort_priority: int
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


class ShelvesNestedForLadderOutput(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput
    shelf_number: ShelfNumberNestedForLadderOutput
    owner: OwnerNestedForLadderOutput
    size_class_id: int


class LadderDetailReadOutput(LadderBaseOutput):
    sort_priority: int
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
                        "shelf_number": {
                            "number": 3
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
