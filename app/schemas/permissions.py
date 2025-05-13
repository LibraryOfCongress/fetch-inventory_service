from typing import Optional
from pydantic import BaseModel, constr, conint
from datetime import datetime, timezone


class PermissionInput(BaseModel):
    name: constr(max_length=50)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "test"
            }
        }


class PermissionUpdateInput(BaseModel):
    name: Optional[constr(max_length=50)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "test"
            }
        }


class PermissionBaseReadOutput(BaseModel):
    id: int
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "test"
            }
        }


class PermissionListOutput(PermissionBaseReadOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "test"
            }
        }


class PermissionDetailWriteOutput(BaseModel):
    id: int
    name: str
    create_dt: datetime
    update_dt: datetime
    groups: list

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "test",
                "create_dt": "2022-01-01T00:00:00",
                "update_dt": "2022-01-01T00:00:00",
                "groups": [{
                    "id": 1,
                    "name": "test",
                    "create_dt": "2022-01-01T00:00:00",
                    "update_dt": "2022-01-01T00:00:00"
                }]
            }
        }


class PermissionDetailReadOutput(PermissionDetailWriteOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "test",
                "create_dt": "2022-01-01T00:00:00",
                "update_dt": "2022-01-01T00:00:00",
                "groups": [{
                    "id": 1,
                    "name": "test",
                    "create_dt": "2022-01-01T00:00:00",
                    "update_dt": "2022-01-01T00:00:00"
                }]
            }
        }
