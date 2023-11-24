from typing import Optional
from pydantic import BaseModel, conint
from datetime import datetime

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


class ShelfPositionBaseReadOutput(BaseModel):
    id: int
    shelf_id: int
    shelf_position_number_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "shelf_id": 1,
                "shelf_position_number_id": 1,
            }
        }


class ShelfPositionListOutput(ShelfPositionBaseReadOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "shelf_id": 1,
                "shelf_position_number_id": 1,
            }
        }


class ShelfPositionDetailWriteOutput(BaseModel):
    id: int
    shelf_id: int
    shelf_position_number_id: int
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "shelf_id": 1,
                "shelf_position_number_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class ShelfPositionDetailReadOutput(ShelfPositionBaseReadOutput):
    shelf: ShelfDetailWriteOutput
    shelf_position_number: ShelfPositionNumberDetailOutput
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
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "shelf": {
                    "id": 1,
                    "ladder_id": 1,
                    "capacity": 33,
                    "shelf_number_id": 1,
                    "container_type_id": 1,
                    "height": 15.7,
                    "width": 30.33,
                    "depth": 27,
                    "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
