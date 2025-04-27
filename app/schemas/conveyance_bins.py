import uuid

from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone

from app.schemas.barcodes import BarcodeDetailReadOutput


class ConveyanceBinInput(BaseModel):
    barcode_id: Optional[uuid.UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }


class ConveyanceBinBaseReadOutput(BaseModel):
    id: int
    barcode_id: Optional[uuid.UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }


class ConveyanceBinListOutput(ConveyanceBinBaseReadOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }


class ConveyanceBinDetailWriteOutput(BaseModel):
    id: int
    barcode_id: Optional[uuid.UUID] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class ConveyanceBinDetailReadOutput(ConveyanceBinBaseReadOutput):
    barcode: BarcodeDetailReadOutput
    trays: list
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "Tray",
                "barcode": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "value": "5901234123457",
                    "type_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "trays": [
                    "..."
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
