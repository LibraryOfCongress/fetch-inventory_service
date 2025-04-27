import uuid

from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class BarcodeInput(BaseModel):
    value: str
    type: str

    class Config:
        json_schema_extra = {
            "example": {
                "value": "5901234123457",
                "type": "Tray"
            }
        }


class BarcodeMutationInput(BaseModel):
    """This is not user facing"""

    value: str
    type_id: int


class BarcodeUpdateInput(BaseModel):
    value: Optional[str] = None
    type: Optional[str] = None
    withdrawn: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "value": "5901234123457",
                "type": "Item",
                "withdrawn": True
            }
        }


class BarcodeListOutput(BaseModel):
    id: uuid.UUID | None
    value: str
    type_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "value": "5901234123457",
                "type_id": 1
            }
        }


class NestedBarcodeTypeOutputForBarcode(BaseModel):
    id: int
    name: str


class BarcodeDetailWriteOutput(BaseModel):
    id: uuid.UUID | None
    value: str
    withdrawn: bool
    type_id: int
    type: NestedBarcodeTypeOutputForBarcode
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "value": "5901234123457",
                "type_id": 2,
                "type": {
                    "id": 2,
                    "name": "Tray"
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class BarcodeDetailReadOutput(BarcodeDetailWriteOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "value": "5901234123457",
                "type_id": 1,
                "type": {
                    "id": 1,
                    "name": "Item"
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
