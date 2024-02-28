import uuid

from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.accession_jobs import AccessionJobBaseOutput
from app.schemas.verification_jobs import VerificationJobBaseOutput
from app.schemas.media_types import MediaTypeDetailReadOutput
from app.schemas.size_class import SizeClassDetailReadOutput
from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.subcollection import SubcollectionDetailWriteOutput


class NonTrayItemInput(BaseModel):
    accession_job_id: Optional[int] = None
    verification_job_id: Optional[int] = None
    container_type_id: Optional[int] = None
    owner_id: Optional[int] = None
    subcollection_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None
    barcode_id: Optional[uuid.UUID] = None
    accession_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "accession_job_id": 1,
                "verification_job_id": 1,
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
                "accession_job_id": 1,
                "verification_job_id": 1,
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


class NonTrayItemBaseOutput(NonTrayItemInput):
    id: int


class NonTrayItemListOutput(NonTrayItemBaseOutput):

    class Config:
        json_schema_extra = {
            "example": {
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
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class NonTrayItemDetailWriteOutput(NonTrayItemBaseOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
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
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class NonTrayItemDetailReadOutput(NonTrayItemDetailWriteOutput):
    barcode: BarcodeDetailReadOutput
    media_type: MediaTypeDetailReadOutput
    size_class: SizeClassDetailReadOutput
    accession_job: AccessionJobBaseOutput
    verification_job: VerificationJobBaseOutput
    subcollection: SubcollectionDetailWriteOutput
    owner: Optional[OwnerDetailReadOutput] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "accession_job_id": 1,
                "verification_job_id": 1,
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
