from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class UserInput(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "Frodo",
                "last_name": "Baggins"
            }
        }


class UserUpdateInput(UserInput):

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "Frodo",
                "last_name": "Baggins"
            }
        }


class UserBaseReadOutput(UserUpdateInput):
    id: int


class UserListOutput(UserBaseReadOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "first_name": "Bilbo",
                "last_name": "Baggins"
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
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
