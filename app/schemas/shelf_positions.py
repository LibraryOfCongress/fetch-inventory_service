from typing import Optional
from pydantic import BaseModel, conint, constr
from datetime import datetime

from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.shelves import ShelfDetailWriteOutput
from app.schemas.shelf_position_numbers import ShelfPositionNumberDetailOutput


class ShelfPositionInput(BaseModel):
    shelf_position_number_id: conint(ge=0, le=9223372036854775807)
    shelf_id: conint(ge=0, le=2147483647)

    class Config:
        json_schema_extra = {
            "example": {
                "shelf_id": 1,
                "shelf_position_number_id": 1,
            }
        }


class ShelfPositionUpdateInput(BaseModel):
    shelf_position_number_id: Optional[conint(ge=0, le=9223372036854775807)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "shelf_position_number_id": 1
            }
        }


class ShelfPositionBaseReadOutput(BaseModel):
    id: int
    shelf_id: int
    shelf_position_number_id: int
    location: Optional[str] = None
    internal_location: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "shelf_id": 1,
                "shelf_position_number_id": 1,
                "location": "Cabin Branch-04-57-L-23-10-08",
                "internal_location": "01-04-57-L-23-10-08"
            }
        }


class NestedShelfPositionNumberForShelvingPositionList(BaseModel):
    number: int

class ShelfPositionListOutput(ShelfPositionBaseReadOutput):
    shelf_position_number: NestedShelfPositionNumberForShelvingPositionList

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "shelf_id": 1,
                "shelf_position_number_id": 1,
                "shelf_position_number": {
                    "number": 1
                }
            }
        }


class ShelfPositionDetailWriteOutput(BaseModel):
    id: int
    shelf_id: int
    shelf_position_number_id: int
    location: Optional[str] = None
    internal_location: Optional[str] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "shelf_id": 1,
                "shelf_position_number_id": 1,
                "location": "Cabin Branch-04-57-L-23-10-08",
                "internal_location": "01-04-57-L-23-10-08",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


class TrayNestedForShelfPositionOutput(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput


class NonTrayNestedForShelfPositionOutput(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput


class ShelfPositionDetailReadOutput(ShelfPositionBaseReadOutput):
    shelf: ShelfDetailWriteOutput
    shelf_position_number: ShelfPositionNumberDetailOutput
    tray: Optional[TrayNestedForShelfPositionOutput] = None
    non_tray_item: Optional[NonTrayNestedForShelfPositionOutput] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "shelf_id": 1,
                "shelf_position_number_id": 1,
                "shelf_position_number": {
                    "id": 1,
                    "number": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "shelf": {
                    "id": 1,
                    "ladder_id": 1,
                    "shelf_type": {
                        "id": 1,
                        "type": "Long",
                        "size_class_id": 1,
                        "size_class": {
                            "id": 1,
                            "name": "C-Low",
                            "short_name": "CL",
                            "assigned": False
                        },
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398",
                    },
                    "available_space": 30,
                    "shelf_number_id": 1,
                    "container_type_id": 1,
                    "height": 15.7,
                    "width": 30.33,
                    "depth": 27,
                    "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "tray": {
                    "id": 1,
                    "barcode": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "value": "5901234123457",
                        "type_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                },
                "non_tray_item": {
                    "id": 1,
                    "barcode": {
                        "id": "5532y8400-e29b-41d4-a716-446655440000",
                        "value": "6901234123457",
                        "type_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
