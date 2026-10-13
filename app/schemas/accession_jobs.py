# /code/app/schemas/accession_jobs.py - FINAL SCHEMAS FIX

import uuid

# All Pydantic V2 imports are correct
from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from app.models.accession_jobs import AccessionJobStatus
from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput
from app.schemas.media_types import MediaTypeDetailReadOutput
from app.schemas.size_class import SizeClassDetailReadOutput
from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.users import UserDetailReadOutput


class AccessionJobInput(BaseModel):
    trayed: bool
    workflow_id: Optional[int] = None
    status: str
    media_type_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    created_by_id: Optional[int] = None
    run_time: Optional[timedelta] = None
    last_transition: Optional[datetime] = None
    owner_id: Optional[int] = None
    size_class_id: Optional[int] = None
    container_type_id: Optional[int] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        # This validator logic is correct for Pydantic V2
        if value is not None and value not in AccessionJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(AccessionJobStatus._member_names_)}"
            )
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trayed": True,
                "workflow_id": None,
                "status": "Created",
                "assigned_user_id": 1,
                "created_by_id": 2,
                "run_time": "03:25:15",
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "owner_id": 1,
                "size_class_id": 1,
                "container_type_id": 1
            }
        }
    )


class AccessionJobUpdateInput(BaseModel):
    trayed: Optional[bool] = None
    status: Optional[str] = None
    assigned_user_id: Optional[int] = None
    owner_id: Optional[int] = None
    size_class_id: Optional[int] = None
    container_type_id: Optional[int] = None
    media_type_id: Optional[int] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        # This validator logic is correct for Pydantic V2
        if value is not None and value not in AccessionJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(AccessionJobStatus._member_names_)}"
            )
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trayed": True,
                "status": "Paused",
                "assigned_user_id": 1,
                "created_by_id": 2,
                "owner_id": 1,
                "size_class_id": 1,
                "container_type_id": 1,
                "media_type_id": 1
            }
        }
    )


class AccessionJobBaseOutput(BaseModel):
    id: int
    workflow_id: Optional[int] = None
    trayed: bool
    status: Optional[str]
    assigned_user_id: Optional[int] = None
    created_by_id: Optional[int] = None
    owner_id: Optional[int] = None
    container_type_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None




class AccessionJobListOutput(AccessionJobBaseOutput):
    assigned_user_id: Optional[int] = None
    created_by_id: Optional[int] = None
    assigned_user: Optional[UserDetailReadOutput] = None
    created_by: Optional[UserDetailReadOutput] = None
    create_dt: datetime
    tray_count: int = 0
    item_count: int = 0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "workflow_id": 1,
                "trayed": True,
                "assigned_user_id": 1,
                "created_by_id": 2,
                "owner_id": 1,
                "media_type_id": 1,
                "size_class_id": 1,
                "container_type_id": 1,
                "status": "Created",
                "create_dt": "2023-10-08T20:46:56.764426",
                "assigned_user": {
                    "id": 1,
                    "first_name": "Frodo",
                    "last_name": "Baggins",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "created_by": {
                    "id": 2,
                    "first_name": "Bilbo",
                    "last_name": "Baggins",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                }
            }
        }
    )



class ItemDetailNestedForAccessionJob(BaseModel):
    # UUID typing is already correct for Pydantic V2
    id: int
    status: Optional[str] = None
    accession_job_id: Optional[int] = None
    scanned_for_accession: Optional[bool] = None
    verification_job_id: Optional[int] = None
    tray_id: Optional[int] = None
    container_type_id: Optional[int] = None
    owner_id: Optional[int] = None
    title: Optional[str] = None
    volume: Optional[str] = None
    condition: Optional[str] = None
    arbitrary_data: Optional[str] = None
    subcollection_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None
    barcode_id: Optional[uuid.UUID] = None
    withdrawn_barcode_id: Optional[uuid.UUID] = None
    accession_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    withdrawn_barcode: Optional[BarcodeDetailReadOutput] = None


class TrayDetailNestedForAccessionJob(BaseModel):
    # UUID typing is already correct for Pydantic V2
    id: int
    accession_job_id: Optional[int] = None
    scanned_for_accession: Optional[bool] = None
    collection_accessioned: Optional[bool] = None
    verification_job_id: Optional[int] = None
    container_type_id: Optional[int] = None
    owner_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    media_type_id: Optional[int] = None
    conveyance_bin_id: Optional[int] = None
    size_class_id: Optional[int] = None
    barcode_id: Optional[uuid.UUID] = None
    withdrawn_barcode_id: Optional[uuid.UUID] = None
    accession_dt: Optional[datetime] = None
    shelved_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    withdrawn_barcode: Optional[BarcodeDetailReadOutput] = None


class NonTrayItemDetailNestedForAccessionJob(BaseModel):
    # UUID typing is already correct for Pydantic V2
    id: int
    status: Optional[str] = None
    accession_job_id: Optional[int] = None
    scanned_for_accession: Optional[bool] = None
    verification_job_id: Optional[int] = None
    container_type_id: Optional[int] = None
    owner_id: Optional[int] = None
    subcollection_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None
    barcode_id: Optional[uuid.UUID] = None
    withdrawn_barcode_id: Optional[uuid.UUID] = None
    accession_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    withdrawn_barcode: Optional[BarcodeDetailReadOutput] = None


class AccessionJobDetailOutput(AccessionJobBaseOutput):
    assigned_user_id: Optional[int] = None
    created_by_id: Optional[int] = None
    run_time: Optional[timedelta]
    last_transition: Optional[datetime] = None
    owner_id: Optional[int] = None
    container_type_id: Optional[int] = None
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    media_type_id: Optional[int] = None
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    owner: Optional[OwnerDetailReadOutput] = None
    verification_job: Optional[list] = None
    items: List[ItemDetailNestedForAccessionJob]
    trays: List[TrayDetailNestedForAccessionJob]
    non_tray_items: List[NonTrayItemDetailNestedForAccessionJob]
    assigned_user: Optional[UserDetailReadOutput] = None
    created_by: Optional[UserDetailReadOutput] = None
    create_dt: datetime
    update_dt: datetime

    # NOTE: The format_run_time is a Pydantic V2 class method and is correctly defined.
    @field_validator("run_time", mode="before") 
    @classmethod
    def format_run_time(cls, v) -> str:
        if isinstance(v, timedelta):
            total_seconds = int(v.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "workflow_id": 1,
                "trayed": True,
                "status": "Paused",
                "user_id": 1,
                "created_by_id": 2,
                "assigned_user": {
                    "id": 1,
                    "first_name": "Frodo",
                    "last_name": "Baggins",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "created_by": {
                    "id": 2,
                    "first_name": "Bilbo",
                    "last_name": "Baggins",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "run_time": "03:25:15",
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "owner_id": 1,
                "size_class_id": 1,
                "size_class": {
                    "id": 1,
                    "name": "C-Low",
                    "short_name": "CL",
                    "height": 15.7,
                    "width": 30.33,
                    "depth": 27,
                    "create_dt": "2023-11-27T12:34:56.789123Z",
                    "update_dt": "2023-11-27T12:34:56.789123Z"
                },
                "container_type_id": 1,
                "media_type_id": 1,
                "media_type": {
                    "id": 1,
                    "name": "Book",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "owner": {
                    "id": 1,
                    "name": "Special Collection Directorate",
                    "owner_tier_id": 2,
                    "owner_tier": {
                        "id": 1,
                        "level": 2,
                        "name": "division",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "container_type": {
                    "id": 1,
                    "type": "Tray",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "verification_job": [
                    {
                        "id": 1,
                        "status": "Created",
                        "assigned_user_id": 1,
                        "last_transition": "2023-11-27T12:34:56.789123Z",
                        "run_time": "03:25:15",
                        "accession_job_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                ],
                "items": ["..."],
                "trays": ["..."],
                "non_tray_items": ["..."],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
    )