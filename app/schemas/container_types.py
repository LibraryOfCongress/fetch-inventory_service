import uuid

from typing import Optional
from pydantic import BaseModel, constr
from datetime import datetime

class ContainerTypeInput(BaseModel):
    type: constr(max_length=25)

    class Config:
        json_schema_extra = {
            "example": {
                "type": "Tray"
            }
        }


class ContainerTypeBaseReadOutput(BaseModel):
    id: int
    type: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "Non-Tray"
            }
        }


class ContainerTypeListOutput(ContainerTypeBaseReadOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "Tray"
            }
        }


class ContainerTypeDetailWriteOutput(BaseModel):
    id: int
    type: str
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "Tray",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class ContainerTypeDetailReadOutput(ContainerTypeBaseReadOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "Tray",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
