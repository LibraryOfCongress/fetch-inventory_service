import uuid

from typing import Optional
from pydantic import BaseModel, constr, ConfigDict
from datetime import datetime, timezone

class ContainerTypeInput(BaseModel):
    type: constr(max_length=25)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "Tray"
            }
        }
    )


class ContainerTypeBaseReadOutput(BaseModel):
    id: int
    type: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "type": "Non-Tray"
            }
        }
    )


class ContainerTypeListOutput(ContainerTypeBaseReadOutput):

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "type": "Tray"
            }
        }
    )


class ContainerTypeDetailWriteOutput(BaseModel):
    id: int
    type: str
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "type": "Tray",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
    )


class ContainerTypeDetailReadOutput(ContainerTypeBaseReadOutput):
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "type": "Tray",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
    )
