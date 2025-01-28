from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, computed_field

from app.models.verification_changes import VerificationChangeStatus
from app.schemas.users import UserDetailReadOutput


class VerificationChangeInput(BaseModel):
    workflow_id: Optional[int] = None
    tray_barcode_value: Optional[str] = None
    item_barcode_value: Optional[str] = None
    completed_by_id: Optional[int] = None
    change_type: Optional[str] = None

    @field_validator("change_type", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in VerificationChangeStatus._member_names_:
            raise ValueError(
                f"Invalid change type: {value}. Must be one of"
                f" {list(VerificationChangeStatus._member_names_)}"
                )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": 1,
                "tray_barcode_value": "12345678900",
                "item_barcode_value": "12345678901",
                "completed_by_id": 1,
                "change_type": "Added"
            }
        }


class VerificationChangeUpdateInput(VerificationChangeInput):
    create_dt: Optional[datetime] = None
    update_dt: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "verification_job_id": 1,
                "tray_barcode_value": "12345678900",
                "item_barcode_value": "12345678901",
                "completed_by_id": 1,
                "change_type": "Added",
                "create_dt": "2023-11-27T12:34:56.789123Z",
                "update_dt": "2023-11-27T12:34:56.789123Z"
            }
        }


class VerificationChangeBaseOutput(BaseModel):
    id: int
    change_type: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "change_type": "Added"
            }
        }


class VerificationChangeListOutput(VerificationChangeBaseOutput):
    workflow_id: Optional[int] = None
    tray_barcode_value: Optional[str] = None
    item_barcode_value: Optional[str] = None
    completed_by_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "workflow_id": 1,
                "tray_barcode_value": "12345678900",
                "item_barcode_value": "12345678901",
                "user_id": 1,
                "change_type": "Added"
            }
        }


class VerificationChangeDetailOutput(VerificationChangeBaseOutput):
    workflow_id: Optional[int] = None
    tray_barcode_value: Optional[str] = None
    item_barcode_value: Optional[str] = None
    completed_by_id: Optional[int] = None
    create_dt: Optional[datetime] = None
    update_dt: Optional[datetime] = None
    created_by: Optional[UserDetailReadOutput] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "workflow_id": 1,
                "tray_barcode_value": "12345678900",
                "item_barcode_value": "12345678901",
                "completed_by_id": 1,
                "change_type": "Added",
                "create_dt": "2023-11-27T12:34:56.789123Z",
                "update_dt": "2023-11-27T12:34:56.789123Z",
                "created_by": {
                    "id": 1,
                    "first_name": "John",
                    "last_name": "Doe",
                    "name": "John Doe",
                    "email": "lYK2o@example.com",
                    "create_dt": "2023-11-27T12:34:56.789123Z",
                    "update_dt": "2023-11-27T12:34:56.789123Z"
                }
            }
        }
