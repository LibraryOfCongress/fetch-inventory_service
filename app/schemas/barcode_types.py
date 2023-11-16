from pydantic import BaseModel
from datetime import datetime


class BarcodeTypesInput(BaseModel):
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "name": "qrcode",
            }
        }


class BarcodeTypesListOutput(BaseModel):
    id: int
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "qrcode",
            }
        }


class BarcodeTypesDetailWriteOutput(BaseModel):
    id: int
    name: str
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "qrcode",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


class BarcodeTypesDetailReadOutput(BaseModel):
    id: int
    name: str
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "qrcode",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
