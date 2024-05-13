import uuid

from typing import Optional
from pydantic import BaseModel, field_validator
from datetime import datetime

from app.models.non_tray_items import NonTrayItemStatus
from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.accession_jobs import AccessionJobBaseOutput
from app.schemas.verification_jobs import VerificationJobBaseOutput
from app.schemas.media_types import MediaTypeDetailReadOutput
from app.schemas.size_class import SizeClassDetailReadOutput
from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.subcollection import SubcollectionDetailWriteOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput
from app.schemas.shelving_jobs import ShelvingJobBaseOutput


class NonTrayItemInput(BaseModel):
    status: Optional[str] = None
    accession_job_id: Optional[int] = None
    scanned_for_accession: Optional[bool] = None
    scanned_for_verification: Optional[bool] = None
    scanned_for_shelving: Optional[bool] = None
    verification_job_id: Optional[int] = None
    shelving_job_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    shelf_position_proposed_id: Optional[int] = None
    container_type_id: Optional[int] = None
    owner_id: Optional[int] = None
    subcollection_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None
    barcode_id: Optional[uuid.UUID] = None
    accession_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in NonTrayItemStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(NonTrayItemStatus._member_names_)}"
            )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "status": "In",
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
                "scanned_for_shelving": False,
                "verification_job_id": 1,
                "shelving_job_id": 1,
                "shelf_position_id": 1,
                "shelf_position_proposed_id": 1,
                "container_type_id": 1,
                "owner_id": 1,
                "subcollection_id": 1,
                "media_type_id": 1,
                "size_class_id": 1,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "accession_dt": "2023-10-08T20:46:56.764426",
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class NonTrayItemUpdateInput(NonTrayItemInput):

    class Config:
        json_schema_extra = {
            "example": {
                "status": "In",
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
                "scanned_for_shelving": False,
                "verification_job_id": 1,
                "shelving_job_id": 1,
                "shelf_position_id": 1,
                "shelf_position_proposed_id": 1,
                "container_type_id": 1,
                "owner_id": 1,
                "subcollection_id": 1,
                "media_type_id": 1,
                "size_class_id": 1,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "accession_dt": "2023-10-08T20:46:56.764426",
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class NestedShelfPositionNumberNonTray(BaseModel):
    number: int


class ShelfPositionNestedForNonTrayOutput(BaseModel):
    id: int
    shelf_id: int
    shelf_position_number: NestedShelfPositionNumberNonTray


class NonTrayItemBaseOutput(NonTrayItemInput):
    id: int
    shelf_position: Optional[ShelfPositionNestedForNonTrayOutput] = None


class NonTrayItemListOutput(NonTrayItemBaseOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "In",
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
                "scanned_for_shelving": False,
                "verification_job_id": 1,
                "shelving_job_id": 1,
                "shelf_position_id": 1,
                "shelf_position": {
                    "id": 1,
                    "shelf_id": 1,
                    "shelf_position_number": {
                        "number": 1
                    }
                },
                "shelf_position_proposed_id": 1,
                "container_type_id": 1,
                "owner_id": 1,
                "subcollection_id": 1,
                "media_type_id": 1,
                "size_class_id": 1,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "accession_dt": "2023-10-08T20:46:56.764426",
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class NonTrayItemDetailWriteOutput(NonTrayItemBaseOutput):
    barcode: BarcodeDetailReadOutput
    media_type: MediaTypeDetailReadOutput
    size_class: Optional[SizeClassDetailReadOutput]
    container_type: Optional[ContainerTypeDetailReadOutput]
    shelving_job: Optional[ShelvingJobBaseOutput] = None
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
                "scanned_for_shelving": False,
                "verification_job_id": 1,
                "shelving_job_id": 1,
                "shelving_job": {
                    "id": 1,
                    "status": "Created"
                },
                "shelf_position_id": 1,
                "shelf_position": {
                    "id": 1,
                    "shelf_id": 1,
                    "shelf_position_number": {
                        "number": 1
                    }
                },
                "shelf_position_proposed_id": 1,
                "container_type_id": 1,
                "owner_id": 1,
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
                "container_type": {
                    "id": 1,
                    "type": "Non-Tray",
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
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
                },
                "accession_dt": "2023-10-08T20:46:56.764426",
                "withdrawal_dt": "2023-10-08T20:46:56.764426",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class NonTrayItemDetailReadOutput(NonTrayItemDetailWriteOutput):
    accession_job: Optional[AccessionJobBaseOutput] = None
    verification_job: Optional[VerificationJobBaseOutput] = None
    subcollection: Optional[SubcollectionDetailWriteOutput] = None
    owner: Optional[OwnerDetailReadOutput] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "In",
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
                "scanned_for_shelving": False,
                "verification_job_id": 1,
                "shelving_job_id": 1,
                "shelving_job": {
                    "id": 1,
                    "status": "Created"
                },
                "shelf_position_id": 1,
                "shelf_position": {
                    "id": 1,
                    "shelf_id": 1,
                    "shelf_position_number": {
                        "number": 1
                    }
                },
                "shelf_position_proposed_id": 1,
                "container_type_id": 2,
                "owner_id": 1,
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
                "container_type": {
                    "id": 2,
                    "type": "Non-Tray",
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
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398",
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
