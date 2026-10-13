from typing import Optional
from pydantic import BaseModel, conint, constr, ConfigDict
from datetime import datetime, timezone

from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.shelves import ShelfDetailWriteOutput


class ShelfPositionInput(BaseModel):
    position_number: conint(ge=1, le=32767)
    shelf_id: conint(ge=0, le=2147483647)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shelf_id": 1,
                "position_number": 1,
            }
        }
    )


class ShelfPositionUpdateInput(BaseModel):
    position_number: Optional[conint(ge=1, le=32767)] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "position_number": 1
            }
        }
    )


class ShelfPositionBaseReadOutput(BaseModel):
    id: int
    shelf_id: int
    position_number: int
    location: Optional[str] = None
    internal_location: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "shelf_id": 1,
                "position_number": 1,
                "location": "Cabin Branch-04-57-L-23-10-08",
                "internal_location": "01-04-57-L-23-10-08"
            }
        }
    )


class ShelfPositionListOutput(ShelfPositionBaseReadOutput):

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "shelf_id": 1,
                "position_number": 1,
            }
        }
    )


class ShelfPositionDetailWriteOutput(BaseModel):
    id: int
    shelf_id: int
    position_number: int
    location: Optional[str] = None
    internal_location: Optional[str] = None
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "shelf_id": 1,
                "position_number": 1,
                "location": "Cabin Branch-04-57-L-23-10-08",
                "internal_location": "01-04-57-L-23-10-08",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
    )


class TrayNestedForShelfPositionOutput(BaseModel):
    id: int
    barcode: Optional[BarcodeDetailReadOutput] = None


class NonTrayNestedForShelfPositionOutput(BaseModel):
    id: int
    barcode: Optional[BarcodeDetailReadOutput] = None


class ShelfPositionDetailReadOutput(ShelfPositionBaseReadOutput):
    shelf: ShelfDetailWriteOutput
    tray: Optional[TrayNestedForShelfPositionOutput] = None
    non_tray_item: Optional[NonTrayNestedForShelfPositionOutput] = None
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "shelf_id": 1,
                "position_number": 1,
                "shelf": {
                    "id": 1,
                    "ladder_id": 1,
                    "shelf_number": 3,
                    "available_space": 30,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
    )
