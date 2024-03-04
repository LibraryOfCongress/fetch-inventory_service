from typing import Optional
from pydantic import BaseModel, constr
from datetime import datetime


class SizeClassInput(BaseModel):
    name: Optional[constr(max_length=50)] = None
    short_name: Optional[constr(max_length=10)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "C-Low",
                "short_name": "CL"
            }
        }


class SizeClassUpdateInput(SizeClassInput):

    class Config:
        json_schema_extra = {
            "example": {
                "name": "C-Low",
                "short_name": "CL"
            }
        }


class SizeClassBaseOutput(BaseModel):
    id: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1
            }
        }


class SizeClassListOutput(SizeClassBaseOutput):
    name: str
    short_name: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low",
                "short_name": "CL"
            }
        }


class SizeClassDetailWriteOutput(SizeClassBaseOutput):
    name: str
    short_name: str
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low",
                "short_name": "CL",
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
                "short_name": "CL",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
