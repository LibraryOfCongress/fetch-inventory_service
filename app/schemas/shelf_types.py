from datetime import datetime
from typing import Optional

from pydantic import BaseModel, constr
from app.schemas.size_class import SizeClassListOutput, SizeClassDetailReadOutput


class ShelfTypeInput(BaseModel):
    type: constr(min_length=1, max_length=50)
    size_class_id: int
    max_capacity: int

    class Config:
        json_schema_extra = {
            "example": {
                "type": "Tray",
                "size_class_id": 1,
                "max_capacity": 1
            }
        }


class ShelfTypeUpdateInput(BaseModel):
    max_capacity: Optional[int] = None
    type: Optional[constr(min_length=1, max_length=50)] = None
    size_class_id: Optional[int] = None
    # update_dt: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "type": "Full",
                "size_class_id": 1,
                "max_capacity": 30
            }
        }


class ShelfTypeReadOutput(BaseModel):
    id: int
    type: str
    size_class_id: Optional[int] = None


class ShelfTypeListOutput(ShelfTypeReadOutput):
    max_capacity: int
    size_class: Optional[SizeClassListOutput] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "Long",
                "size_class_id": 1,
                "max_capacity": 30,
                "size_class": {
                    "id": 1,
                    "name": "C-Low",
                    "short_name": "CL",
                    "assigned": False
                }
            }
        }


class ShelfTypeDetailOutput(ShelfTypeReadOutput):
    size_class: Optional[SizeClassDetailReadOutput] = None
    # shelves: Optional[list] = None #(Too large, not used)
    max_capacity: Optional[int] = None
    update_dt: Optional[datetime] = None
    create_dt: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "Long",
                "size_class_id": 1,
                "size_class": {
                    "id": 1,
                    "name": "C-Low",
                    "short_name": "CL",
                    "assigned": False,
                    "height": 15.7,
                    "width": 30.33,
                    "depth": 27,
                    "create_dt": "2023-11-27T12:34:56.789123Z",
                    "update_dt": "2023-11-27T12:34:56.789123Z"
                },
                "max_capacity": 30,
                "update_dt": "2023-11-27T12:34:56.789123Z",
                "create_dt": "2023-11-27T12:34:56.789123Z"
            }
        }
