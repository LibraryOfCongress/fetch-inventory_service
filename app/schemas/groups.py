from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class GroupInput(BaseModel):
    name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Technician"
            }
        }


class GroupUpdateInput(GroupInput):

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Technician"
            }
        }


class GroupBaseReadOutput(GroupUpdateInput):
    id: int


class GroupListOutput(GroupBaseReadOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Technician"
            }
        }


class GroupDetailWriteOutput(GroupListOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Technician",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class GroupDetailReadOutput(GroupDetailWriteOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Technician",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class NestedUserForGroupOutput(BaseModel):
    id: int
    first_name: str
    last_name: str


class GroupUserOutput(BaseModel):
    name: str
    users: Optional[List[NestedUserForGroupOutput]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Technician",
                "users": [
                    {
                        "id": 1,
                        "first_name": "Frodo",
                        "last_name": "Baggins"
                    },
                    {
                        "id": 2,
                        "first_name": "Bilbo",
                        "last_name": "Baggins"
                    }
                ]
            }
        }
