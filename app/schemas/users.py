from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timezone

from app.schemas.groups import GroupPermissionsOutput


class UserInput(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    default_building_id: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Frodo",
                "last_name": "Baggins",
                "email": "FBaggins@example.com",
                "default_building_id": 1
            }
        }
    )


class UserUpdateInput(UserInput):

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Frodo",
                "last_name": "Baggins",
                "email": "FBaggins@example.com"
            }
        }
    )


class UserSelfUpdateInput(BaseModel):
    """Restricted self-service update: the fields a user may change on their OWN
    record without admin permissions. Deliberately excludes name/email/groups so
    a non-admin can only adjust personal preferences (e.g. default building)."""
    default_building_id: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "default_building_id": 1
            }
        }
    )


class UserBaseReadOutput(UserUpdateInput):
    id: int
    name: Optional[str] = None


class UserListOutput(UserBaseReadOutput):

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "first_name": "Bilbo",
                "last_name": "Baggins",
                "name": "Bilbo Baggins",
                "email": "FBaggins@example.com"
            }
        }
    )


class UserDetailWriteOutput(UserListOutput):
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class UserDetailReadOutput(UserDetailWriteOutput):

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class NestedGroupForUserOutput(BaseModel):
    id: int
    name: str


class UserGroupOutput(BaseModel):
    groups: Optional[List[NestedGroupForUserOutput]] = []

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class UserPermissionsOutput(BaseModel):
    id: int
    permissions: list

    model_config = ConfigDict(
        json_schema_extra={
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
    )
