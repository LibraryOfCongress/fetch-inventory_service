import uuid

from typing import Optional
from pydantic import BaseModel, field_validator
from datetime import datetime

from app.models.items import ItemStatus
from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.accession_jobs import AccessionJobBaseOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput
from app.schemas.trays import TrayDetailReadOutput
from app.schemas.verification_jobs import VerificationJobBaseOutput
from app.schemas.media_types import MediaTypeDetailReadOutput
from app.schemas.size_class import SizeClassDetailReadOutput
from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.subcollection import SubcollectionDetailWriteOutput


class ItemInput(BaseModel):
    status: Optional[str] = None
    accession_job_id: Optional[int] = None
    scanned_for_accession: Optional[bool] = None
    scanned_for_verification: Optional[bool] = None
    scanned_for_refile_queue: Optional[bool] = None
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

    @field_validator('status', mode='before', check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in ItemStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of "
                f"{list(ItemStatus._member_names_)}"
            )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "status": "In",
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
                "scanned_for_refile_queue": False,
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
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class ItemUpdateInput(ItemInput):
    class Config:
        json_schema_extra = {
            "example": {
                "status": "In",
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
                "scanned_for_refile_queue": False,
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
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class ItemBaseOutput(ItemInput):
    id: int


class ItemListOutput(ItemBaseOutput):
    # media_type, size_class, owner nested serialization is temporary fix
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    owner: Optional[OwnerDetailReadOutput] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "In",
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
                "verification_job_id": 1,
                "container_type_id": 1,
                "tray_id": 1,
                "owner_id": 1,
                "owner": {
                    "id": 1,
                    "name": "Special Collection Directorate",
                    "owner_tier_id": 2,
                    "parent_owner_id": 2,
                    "owner_tier": {
                        "id": 1,
                        "level": 2,
                        "name": "division",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "parent_owner": {
                        "id": 2,
                        "name": "Library of Congress",
                        "owner_tier_id": 1,
                        "parent_owner_id": None,
                        "owner_tier": {
                            "id": 2,
                            "level": 1,
                            "name": "organization",
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "children": [],
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "title": "Lord of The Rings",
                "volume": "I",
                "condition": "Good",
                "arbitrary_data": "Signed copy",
                "subcollection_id": 1,
                "media_type_id": 1,
                "media_type": {
                    "id": 1,
                    "name": "Book",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "size_class_id": 1,
                "size_class": {
                    "id": 1,
                    "name": "C-Low",
                    "short_name": "CL",
                    "assigned": False,
                    "height": 15.7,
                    "width": 30.33,
                    "depth": 27,
                    "create_dt": "2023-11-27T12:34:56.789123Z",
                    "update_dt": "2023-11-27T12:34:56.789123Z"
                },
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "accession_dt": "2023-10-08T20:46:56.764426",
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class ItemDetailWriteOutput(ItemBaseOutput):
    barcode: BarcodeDetailReadOutput
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "In",
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
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
                "barcode": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "value": "5901234123457",
                    "type_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "accession_dt": "2023-10-08T20:46:56.764426",
                "withdrawal_dt": "2023-10-08T20:46:56.764426",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class ItemDetailReadOutput(ItemDetailWriteOutput):
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    accession_job: Optional[AccessionJobBaseOutput] = None
    verification_job: Optional[VerificationJobBaseOutput] = None
    subcollection: Optional[SubcollectionDetailWriteOutput] = None
    owner: Optional[OwnerDetailReadOutput] = None
    tray: Optional[TrayDetailReadOutput] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "In",
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
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
                "barcode": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "value": "5901234123457",
                    "type_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
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
                    "short_name": "CL",
                    "assigned": False,
                    "height": 15.7,
                    "width": 30.33,
                    "depth": 27,
                    "create_dt": "2023-11-27T12:34:56.789123Z",
                    "update_dt": "2023-11-27T12:34:56.789123Z"
                },
                "accession_job": {
                    "id": 1,
                    "trayed": True,
                    "status": "Verified"
                },
                "verification_job": {
                    "id": 1,
                    "trayed": True,
                    "status": "Created"
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
                "subcollection": {
                    "id": 1,
                    "name": "A Song of Ice and Fire",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "accession_dt": "2023-10-08T20:46:56.764426",
                "withdrawal_dt": "2023-10-08T20:46:56.764426",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
