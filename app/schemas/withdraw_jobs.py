import uuid

from pydantic import BaseModel, field_validator
from datetime import datetime, timedelta
from typing import Optional, List

from app.models.withdraw_jobs import WithdrawJobStatus
from app.schemas.items import ItemListOutput
from app.schemas.non_tray_items import NonTrayItemListOutput
from app.schemas.trays import TrayListOutput


class WithdrawJobInput(BaseModel):
    status: Optional[str] = None
    assigned_user_id: Optional[int] = None
    pick_list_id: Optional[int] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in WithdrawJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(WithdrawJobStatus._member_names_)}"
                )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "status": "Created",
                "assigned_user_id": 1,
                "pick_list_id": 1,
            }
        }


class WithdrawJobUpdateInput(BaseModel):
    status: Optional[str] = None
    assigned_user_id: Optional[int] = None
    pick_list_id: Optional[int] = None
    run_time: Optional[timedelta] = None
    run_timestamp: Optional[datetime] = None
    last_transition: Optional[datetime] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in WithdrawJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(WithdrawJobStatus._member_names_)}"
            )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "status": "Created",
                "assigned_user_id": 1,
                "pick_list_id": 1,
                "run_time": "00:00:00",
                "last_transition": "2022-01-01 00:00:00",
                "run_timestamp": "2022-01-01 00:00:00"
            }
        }


class WithdrawJobBaseOutput(BaseModel):
    id: int
    status: str


class WithdrawJobListOutput(WithdrawJobBaseOutput):
    assigned_user_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "Created",
                "assigned_user_id": 1
            }
        }


class WithdrawJobDetailOutput(WithdrawJobBaseOutput):
    assigned_user_id: Optional[int] = None
    last_transition: Optional[datetime] = None
    run_time: timedelta
    items: Optional[List[ItemListOutput]] = None
    trays: Optional[List[TrayListOutput]] = None
    non_tray_items: Optional[List[NonTrayItemListOutput]] = None
    create_dt: datetime
    update_dt: datetime
    errored_barcodes: Optional[List[str]] = None

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
                "status": "Created",
                "assigned_user_id": 1,
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "items": [
                    {
                        "id": 1,
                        "accession_job_id": 1,
                        "verification_job_id": 1,
                        "container_type_id": 1,
                        "tray_id": 1,
                        "owner_id": 1,
                        "title": "Lord of The Rings",
                        "volume": "I",
                        "condition": "Good",
                        "arbitrary_data": "Signed copy",
                        "subcollection_id": 1,
                        "media_type_id": 1,
                        "size_class_id": 1,
                        "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                        "accession_dt": "2023-10-08T20:46:56.764426",
                        "withdrawal_dt": "2023-10-08T20:46:56.764426",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398",
                    }
                ],
                "trays": [
                    {
                        "id": 1,
                        "accession_job_id": 1,
                        "verification_job_id": 1,
                        "container_type_id": 1,
                        "owner_id": 1,
                        "shelving_job_id": 1,
                        "shelf_position_id": 1,
                        "shelf_position_proposed_id": 1,
                        "media_type_id": 1,
                        "conveyance_bin_id": 1,
                        "size_class_id": 1,
                        "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                        "accession_dt": "2023-10-08T20:46:56.764426",
                        "shelved_dt": "2023-10-08T20:46:56.764426",
                        "withdrawal_dt": "2023-10-08T20:46:56.764426",
                    }
                ],
                "non_tray_items": [
                    {
                        "id": 1,
                        "accession_job_id": 1,
                        "verification_job_id": 1,
                        "container_type_id": 1,
                        "owner_id": 1,
                        "shelving_job_id": 1,
                        "shelf_position_id": 1,
                        "shelf_position_proposed_id": 1,
                        "subcollection_id": 1,
                        "media_type_id": 1,
                        "size_class_id": 1,
                        "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                        "accession_dt": "2023-10-08T20:46:56.764426",
                        "withdrawal_dt": "2023-10-08T20:46:56.764426",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398",
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
