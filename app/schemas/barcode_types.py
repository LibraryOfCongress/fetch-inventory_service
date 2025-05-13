from pydantic import BaseModel
from datetime import datetime, timezone


class BarcodeTypesInput(BaseModel):
    name: str
    allowed_pattern: str

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Item",
                "allowed_pattern": "^.{25}$"
            }
        }


class BarcodeTypesListOutput(BaseModel):
    id: int
    name: str
    allowed_pattern: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Item",
                "allowed_pattern": "^.{25}$"
            }
        }


class BarcodeTypesDetailWriteOutput(BaseModel):
    id: int
    name: str
    allowed_pattern: str
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Item",
                "allowed_pattern": "^.{25}$",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class BarcodeTypesDetailReadOutput(BaseModel):
    id: int
    name: str
    allowed_pattern: str
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Item",
                "allowed_pattern": "^.{25}$",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
