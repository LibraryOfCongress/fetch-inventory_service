import uuid

from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.accession_jobs import AccessionJobBaseOutput
from app.schemas.verification_jobs import VerificationJobBaseOutput
from app.schemas.media_types import MediaTypeDetailReadOutput
from app.schemas.size_class import SizeClassDetailReadOutput
from app.schemas.conveyance_bins import ConveyanceBinBaseReadOutput
from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput


class TrayInput(BaseModel):
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
    accession_dt: Optional[datetime] = None
    shelved_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "collection_accessioned": False,
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
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class TrayUpdateInput(TrayInput):

    class Config:
        json_schema_extra = {
            "example": {
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "collection_accessioned": False,
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
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class TrayBaseOutput(TrayInput):
    id: int
    barcode: BarcodeDetailReadOutput
    media_type: MediaTypeDetailReadOutput
    size_class: SizeClassDetailReadOutput

class TrayListOutput(TrayBaseOutput):

    class Config:
        json_schema_extra = {
            "example": [
                {
                    "accession_job_id": 1,
                    "scanned_for_accession": False,
                    "collection_accessioned": False,
                    "verification_job_id": 1,
                    "container_type_id": 1,
                    "owner_id": 1,
                    "shelf_position_id": 1,
                    "media_type_id": 1,
                    "conveyance_bin_id": 1,
                    "size_class_id": 1,
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
                    "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                    "barcode": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "value": "5901234123457",
                        "type_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "accession_dt": "2023-10-08T20:46:56.764426",
                    "shelved_dt": "2023-10-08T20:46:56.764426",
                    "withdrawal_dt": "2023-10-08T20:46:56.764426"
                }
            ]
        }


class TrayDetailWriteOutput(TrayBaseOutput):
    items: list
    owner: Optional[OwnerDetailReadOutput]
    container_type: ContainerTypeDetailReadOutput
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "collection_accessioned": False,
                "verification_job_id": 1,
                "container_type_id": 1,
                "owner_id": 1,
                "shelf_position_id": 1,
                "media_type_id": 1,
                "conveyance_bin_id": 1,
                "size_class_id": 1,
                "items": [
                    "..."
                ],
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "barcode": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "value": "5901234123457",
                    "type_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "accession_dt": "2023-10-08T20:46:56.764426",
                "shelved_dt": "2023-10-08T20:46:56.764426",
                "withdrawal_dt": "2023-10-08T20:46:56.764426",
                "container_type": {
                    "id": 1,
                    "type": "Tray",
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
                }
            }
        }


class TrayDetailReadOutput(TrayDetailWriteOutput):
    conveyance_bin: Optional[ConveyanceBinBaseReadOutput] = None
    accession_job: Optional[AccessionJobBaseOutput] = None
    verification_job: Optional[VerificationJobBaseOutput] = None

    class Config:
        json_schema_extra = {
            "example": {
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "collection_accessioned": False,
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
                "barcode": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "value": "5901234123457",
                    "type_id": 1,
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "container_type": {
                    "id": 1,
                    "type": "Tray",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
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
                "conveyance_bin": {
                    "id": 1,
                    "barcode_id": "550e8400-e29b-41d4-a716-446655440001"
                },
                "items": [
                    "..."
                ],
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
                }
            }
        }
