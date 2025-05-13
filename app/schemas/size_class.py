from typing import Optional
from pydantic import BaseModel, constr, condecimal
from datetime import datetime, timezone


class SizeClassInput(BaseModel):
    name: Optional[constr(max_length=50)] = None
    short_name: Optional[constr(max_length=10)] = None
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "C-Low",
                "short_name": "CL",
                "height": 15.7,
                "width": 30.33,
                "depth": 27
            }
        }


class SizeClassUpdateInput(SizeClassInput):

    class Config:
        json_schema_extra = {
            "example": {
                "name": "C-Low",
                "short_name": "CL",
                "height": 15.7,
                "width": 30.33,
                "depth": 27
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
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low",
                "short_name": "CL",
                "height": 15.7,
                "width": 30.33,
                "depth": 27
            }
        }


class SizeClassDetailWriteOutput(SizeClassBaseOutput):
    name: str
    short_name: str
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "C-Low",
                "short_name": "CL",
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
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
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
