from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone


class SubcollectionInput(BaseModel):
    name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "A Song of Ice and Fire"
            }
        }


class SubcollectionUpdateInput(BaseModel):
    name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "A Song of Ice and Fire"
            }
        }


class SubcollectionBaseReadOutput(BaseModel):
    id: int
    name: Optional[str] = None


class SubcollectionListOutput(SubcollectionBaseReadOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "A Song of Ice and Fire"
            }
        }


class SubcollectionDetailWriteOutput(BaseModel):
    id: int
    name: Optional[str] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "A Song of Ice and Fire",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class SubcollectionDetailReadOutput(BaseModel):
    id: int
    name: Optional[str] = None
    items: Optional[list] = None
    non_tray_items: Optional[list] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "A Song of Ice and Fire",
                "items": [
                    "..."
                ],
                "non_tray_items": [
                    "..."
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
