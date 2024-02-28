from typing import Optional
from pydantic import BaseModel, constr
from datetime import datetime


class SizeClassInput(BaseModel):
    name: Optional[constr(max_length=25)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "C-Low"
            }
        }


class SizeClassUpdateInput(SizeClassInput):

    class Config:
        json_schema_extra = {
            "example": {
                "name": "C-Low"
            }
        }


class SizeClassBaseOutput(SizeClassInput):
    id: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low"
            }
        }


class SizeClassListOutput(SizeClassBaseOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low"
            }
        }


class SizeClassDetailWriteOutput(SizeClassBaseOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


class SizeClassDetailReadOutput(SizeClassDetailWriteOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
