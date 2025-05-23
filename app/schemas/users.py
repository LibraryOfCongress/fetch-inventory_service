from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone

from app.schemas.groups import GroupPermissionsOutput


class UserInput(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "Frodo",
                "last_name": "Baggins",
                "email": "FBaggins@example.com"
            }
        }


class UserUpdateInput(UserInput):

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "Frodo",
                "last_name": "Baggins",
                "email": "FBaggins@example.com"
            }
        }


class UserBaseReadOutput(UserUpdateInput):
    id: int
    name: Optional[str] = None


class UserListOutput(UserBaseReadOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "first_name": "Bilbo",
                "last_name": "Baggins",
                "name": "Bilbo Baggins",
                "email": "FBaggins@example.com"
            }
        }


class UserDetailWriteOutput(UserListOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "first_name": "Bilbo",
                "last_name": "Baggins",
                "name": "Bilbo Baggins",
                "email": "FBaggins@example.com",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class UserDetailReadOutput(UserDetailWriteOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "first_name": "Frodo",
                "last_name": "Baggins",
                "name": "Bilbo Baggins",
                "email": "FBaggins@example.com",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class NestedGroupForUserOutput(BaseModel):
    id: int
    name: str


class UserGroupOutput(BaseModel):
    groups: Optional[List[NestedGroupForUserOutput]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "groups": [
                    {
                        "id": 1,
                        "name": "Technician"
                    },
                    {
                        "id": 2,
                        "name": "Administrator"
                    }
                ]
            }
        }


class UserPermissionsOutput(BaseModel):
    id: int
    permissions: list

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "permissions": [
                    "...",
                    "Create User",
                    "View User",
                    "Update User",
                    "..."
                ]
            }
        }
