from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, field_validator

from app.schemas.requests import RequestListOutput
from app.schemas.users import UserDetailWriteOutput
from app.schemas.withdraw_jobs import WithdrawJobBaseOutput
from app.models.batch_upload import BatchUploadStatus


class BatchUploadInput(BaseModel):
    user_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1
            }
        }


class BatchUploadUpdateInput(BaseModel):
    user_id: Optional[int] = None
    status: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    withdraw_job_id: Optional[int] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in BatchUploadStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(BatchUploadStatus._member_names_)}"
            )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "status": "New",
                "file_name": "test.csv",
                "file_size": 1000,
                "file_type": "text/csv",
                "withdraw_job_id": 1
            }
        }


class BatchUploadBaseOutput(BaseModel):
    id: int
    status: str


class BatchUploadListOutput(BatchUploadBaseOutput):
    user_id: Optional[int] = None
    file_name: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    withdraw_job_id: Optional[int] = None
    requests: Optional[List[RequestListOutput]] = None
    user: Optional[UserDetailWriteOutput] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "New",
                "user_id": 1,
                "file_name": "test.csv",
                "file_size": 1000,
                "file_type": "text/csv",
                "withdraw_job_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class BatchUploadDetailOutput(BatchUploadBaseOutput):
    user_id: Optional[int] = None
    file_name: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    withdraw_job_id: Optional[int] = None
    requests: Optional[List[RequestListOutput]] = None
    withdraw_job: Optional[WithdrawJobBaseOutput] = None
    user: Optional[object] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "New",
                "user_id": 1,
                "file_name": "test.csv",
                "file_size": 1000,
                "file_type": "text/csv",
                "request_id": 1,
                "withdraw_job_id": 1,
                "request": [{
                    "id": 1,
                    "building_id": 1,
                    "request_type_id": 1,
                    "item_id": 1,
                    "non_tray_item_id": 1,
                    "delivery_location_id": 1,
                    "priority_id": 1,
                    "external_request_id": "test",
                    "requestor_name": "test",
                    "scanned_for_pick_list": False,
                    "scanned_for_retrieval": False
                }],
                "withdraw_job": {
                    "id": 1,
                    "status": "Created",
                    "assigned_user_id": 1,
                    "run_time": "00:00:00",
                    "run_timestamp": "2022-01-01 00:00:00",
                    "last_transition": "2022-01-01 00:00:00",
                    "items": {
                        "id": 1
                    },
                    "non_tray_items": {
                        "id": 1
                    },
                    "trays": {
                        "id": 1
                    },
                    "item_count": 1,
                    "tray_count": 1,
                    "non_tray_item_count": 1,
                },
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }

