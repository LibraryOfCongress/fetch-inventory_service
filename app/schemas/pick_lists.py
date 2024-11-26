from typing import Optional, List
from pydantic import BaseModel, field_validator, computed_field
from datetime import datetime, timedelta

from app.models.pick_lists import PickListStatus
from app.schemas.buildings import BuildingBaseOutput
from app.schemas.requests import (
    RequestDetailReadOutputNoPickList, RequestUpdateInput
)
from app.schemas.users import UserDetailReadOutput, UserListOutput
from app.schemas.withdraw_jobs import WithdrawJobBaseOutput, WithdrawJobDetailOutput


class PickListInput(BaseModel):
    created_by_id: Optional[int] = None
    request_ids: list[int]
    errored_request_ids: Optional[list[int]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "request_ids": [1, 2, 3],
                "errored_request_ids": [4, 5, 6]
            }
        }


class PickListUpdateInput(BaseModel):
    user_id: Optional[int] = None
    created_by_id: Optional[int] = None
    status: Optional[str] = None
    building_id: Optional[int] = None
    last_transition: Optional[datetime] = None
    run_time: Optional[timedelta] = None
    run_timestamp: Optional[datetime] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in PickListStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(PickListStatus._member_names_)}"
            )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "created_by_id": 2,
                "status": "Created",
                "building_id": 1,
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "run_timestamp": "2023-11-27T12:34:56.789123Z"
            }
        }


class PickListUpdateRequestInput(RequestUpdateInput):
    run_timestamp: Optional[datetime] = None
    status: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "created_by_id": 2,
                "building_id": 1,
                "status": "Out",
                "run_timestamp": "2023-11-27T12:34:56.789123Z",
                "barcode_value": "RS4321",
                "request_type_id": 1,
                "item_id": 1,
                "non_tray_item_id": None,
                "delivery_location_id": 1,
                "priority_id": 1,
                "requestor_name": "Bilbo Baggins",
                "external_request_id": "12345",
                "scanned_for_pick_list": False,
                "scanned_for_retrieval": False,
            }
        }


class PickListBaseOutput(BaseModel):
    id: int
    user_id: Optional[int] = None
    created_by_id: Optional[int] = None
    user: Optional[UserListOutput] = None
    created_by: Optional[UserListOutput] = None
    building_id: Optional[int] = None
    status: str
    last_transition: Optional[datetime] = None
    run_time: Optional[timedelta] = None
    requests: Optional[list[RequestDetailReadOutputNoPickList]] = None
    withdraw_jobs: Optional[list[WithdrawJobBaseOutput]] = None
    building: Optional[BuildingBaseOutput] = None
    create_dt: datetime
    update_dt: datetime

    @computed_field(title='Request Count')
    @property
    def request_count(self) -> int:
        return len(self.requests)

    @field_validator("run_time")
    @classmethod
    def format_run_time(cls, v) -> str:
        if isinstance(v, timedelta):
            total_seconds = int(v.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "created_by_id": 2,
                "user": {
                    "id": 1,
                    "first_name": "John",
                    "last_name": "Doe",
                },
                "created_by": {
                    "id": 2,
                    "first_name": "Jane",
                    "last_name": "Doe",
                },
                "building_id": 1,
                "status": "Created",
                "request_count": 1,
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764426"
            }
        }


class PickListListOutput(PickListBaseOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "created_by_id": 2,
                "user": {
                    "id": 1,
                    "first_name": "John",
                    "last_name": "Doe",
                },
                "created_by": {
                    "id": 2,
                    "first_name": "Jane",
                    "last_name": "Doe",
                },
                "building_id": 1,
                "status": "Created",
                "request_count": 1,
                "requests": [{
                    "id": 1,
                    "item_id": 1,
                    "delivery_location_id": 1,
                    "priority_id": 1,
                    "pick_list_id": 1,
                    "scanned_for_pick_list": False,
                    "requestor_name": "Bilbo Baggins",
                    "request_type_id": 1,
                    "non_tray_item_id": None,
                    "external_request_id": "12345",
                    "create_dt": "2024-05-15T18:13:31.525080",
                    "update_dt": "2024-05-15T18:13:31.525091",
                    "...": "..."
                }],
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764426"
            }
        }


class PickListDetailOutput(PickListBaseOutput):
    user: Optional[UserDetailReadOutput] = None
    created_by: Optional[UserDetailReadOutput] = None
    requests: Optional[list[RequestDetailReadOutputNoPickList]] = None
    withdraw_jobs: Optional[list[WithdrawJobDetailOutput]] = None
    building_id: Optional[int] = None
    building: Optional[BuildingBaseOutput] = None
    errored_request_ids: Optional[list[int]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "Created",
                "request_count": 1,
                "user_id": 1,
                "created_by_id": 2,
                "user": {
                    "id": 1,
                    "name": "Bilbo Baggins",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764426"
                },
                "created_by": {
                    "id": 2,
                    "name": "Frodo Baggins",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764426"
                },
                "requests": [{
                    "id": 1,
                    "item_id": 1,
                    "delivery_location_id": 1,
                    "priority_id": 1,
                    "pick_list_id": 1,
                    "scanned_for_pick_list": False,
                    "requestor_name": "Bilbo Baggins",
                    "request_type_id": 1,
                    "non_tray_item_id": None,
                    "external_request_id": "12345",
                    "create_dt": "2024-05-15T18:13:31.525080",
                    "update_dt": "2024-05-15T18:13:31.525091",
                    "...": "..."
                }],
                "building_id": 1,
                "building": {
                    "id": 1,
                    "name": "Main"
                },
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764426",
                "errored_request_ids": [4, 5, 6]
            }
        }
