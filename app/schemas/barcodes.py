import uuid

from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class BarcodeInput(BaseModel):
    value: str
    type_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "value": "5901234123457",
                "type_id": 1
            }
        }


class BarcodeUpdateInput(BaseModel):
    value: Optional[str] = None
    type_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "value": "5901234123457",
                "type_id": 1
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


class BarcodeDetailWriteOutput(BaseModel):
    id: uuid.UUID | None
    value: str
    type_id: int
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "value": "5901234123457",
                "type_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class BarcodeDetailReadOutput(BaseModel):
    id: uuid.UUID | None
    value: str
    type_id: int
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "value": "5901234123457",
                "type_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
