import uuid

from pydantic import BaseModel, field_validator
from datetime import datetime, timedelta
from typing import Optional, List

from app.schemas.accession_jobs import AccessionJobDetailOutput
from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput
from app.schemas.shelving_jobs import ShelvingJobDetailOutput
from app.schemas.media_types import MediaTypeDetailReadOutput
from app.schemas.size_class import SizeClassDetailReadOutput
from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.users import UserDetailReadOutput


class VerificationJobInput(BaseModel):
    trayed: bool
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None
    status: Optional[str] = None
    user_id: Optional[int] = None
    last_transition: Optional[datetime] = None
    run_time: Optional[timedelta] = None
    accession_job_id: Optional[int] = None
    owner_id: int
    container_type_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "trayed": True,
                "status": "Created",
                "user_id": 1,
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "accession_job_id": 1,
                "owner_id": 1,
                "container_type_id": 1,
                "media_type_id": 1,
                "size_class_id": 1
            }
        }


class VerificationJobUpdateInput(BaseModel):
    trayed: Optional[bool] = None
    status: Optional[str] = None
    user_id: Optional[int] = None
    last_transition: Optional[datetime] = None
    run_time: Optional[timedelta] = None
    accession_job_id: Optional[int] = None
    owner_id: Optional[int] = None
    container_type_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "trayed": True,
                "status": "Created",
                "user_id": 1,
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "accession_job_id": 1,
                "owner_id": 1,
                "container_type_id": 1,
                "media_type_id": 1,
                "size_class_id": 1
            }
        }


class VerificationJobBaseOutput(BaseModel):
    id: int
    trayed: bool
    status: Optional[str]
    owner_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None


class VerificationJobListOutput(VerificationJobBaseOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "trayed": True,
                "owner_id": 1,
                "status": "Created"
            }
        }


class ItemDetailNestedForVerificationJob(BaseModel):
    id: int
    status: Optional[str] = None
    accession_job_id: Optional[int] = None
    scanned_for_accession: Optional[bool] = None
    scanned_for_verification: Optional[bool] = None
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
    accession_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    barcode: BarcodeDetailReadOutput


class TrayDetailNestedForVerificationJob(BaseModel):
    id: int
    accession_job_id: Optional[int] = None
    scanned_for_accession: Optional[bool] = None
    scanned_for_verification: Optional[bool] = None
    collection_accessioned: Optional[bool] = None
    collection_verified: Optional[bool] = None
    verification_job_id: Optional[int] = None
    container_type_id: Optional[int] = None
    owner_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    media_type_id: Optional[int] = None
    conveyance_bin_id: Optional[int] = None
    size_class_id: Optional[int] = None
    barcode_id: Optional[uuid.UUID] = None
    accession_dt: Optional[datetime] = None
    shelved_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    barcode: BarcodeDetailReadOutput


class NonTrayItemDetailNestedForVerificationJob(BaseModel):
    id: int
    status: Optional[str] = None
    accession_job_id: Optional[int] = None
    scanned_for_accession: Optional[bool] = None
    scanned_for_verification: Optional[bool] = None
    verification_job_id: Optional[int] = None
    container_type_id: Optional[int] = None
    owner_id: Optional[int] = None
    subcollection_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None
    barcode_id: Optional[uuid.UUID] = None
    accession_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    barcode: BarcodeDetailReadOutput


class VerificationJobDetailOutput(VerificationJobBaseOutput):
    user_id: Optional[int] = None
    user: Optional[UserDetailReadOutput] = None
    last_transition: Optional[datetime]
    run_time: Optional[timedelta]
    accession_job_id: Optional[int]
    owner_id: Optional[int] = None
    container_type_id: Optional[int] = None
    owner: Optional[OwnerDetailReadOutput] = None
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    shelving_job: Optional[ShelvingJobDetailOutput] = None
    accession_job: Optional[AccessionJobDetailOutput] = None
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    items: List[ItemDetailNestedForVerificationJob]
    trays: List[TrayDetailNestedForVerificationJob]
    non_tray_items: List[NonTrayItemDetailNestedForVerificationJob]
    shelving_job_id: Optional[int] = None
    create_dt: datetime
    update_dt: datetime

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
                "trayed": True,
                "status": "Created",
                "user_id": 1,
                "user": {
                    "id": 1,
                    "first_name": "Frodo",
                    "last_name": "Baggins",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "accession_job_id": 1,
                "owner_id": 1,
                "container_type_id": 1,
                "shelving_job_id": 1,
                "owner": {
                    "id": 1,
                    "name": "Special Collection Directorate",
                    "owner_tier_id": 2,
                    "owner_tier": {
                        "id": 1,
                        "level": 2,
                        "name": "division",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398",
                    },
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "media_type": {
                    "id": 1,
                    "name": "Book",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "size_class": {
                    "id": 1,
                    "name": "C-Low",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "container_type": {
                    "id": 1,
                    "type": "Tray",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "shelving_job": {
                    "id": 1,
                    "shelving_dt": "2023-10-08T20:46:56.764426",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "accession_job": {
                    "id": 1,
                    "accession_dt": "2023-10-08T20:46:56.764426",
                    "withdrawal_dt": "2023-10-08T20:46:56.764426",
                    "title": "Lord of The Rings",
                    "volume": "I",
                    "condition": "Good",
                    "arbitrary_data": "Signed copy",
                    "subcollection_id": 1,
                    "media_type_id": 1,
                    "size_class_id": 1,
                    "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                    "owner_id": 1,
                    "container_type_id": 1,
                    "tray_id": 1,
                    "shelving_job_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
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
                        "shelf_position_id": 1,
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
                "media_type_id": 1,
                "size_class_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
