import uuid

from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.accession_jobs import AccessionJobBaseOutput
from app.schemas.verification_jobs import VerificationJobBaseOutput
from app.schemas.shelving_jobs import ShelvingJobBaseOutput
from app.schemas.media_types import MediaTypeDetailReadOutput
from app.schemas.size_class import SizeClassDetailReadOutput
from app.schemas.conveyance_bins import ConveyanceBinBaseReadOutput
from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput


class TrayInput(BaseModel):
    accession_job_id: Optional[int] = None
    scanned_for_accession: Optional[bool] = None
    scanned_for_verification: Optional[bool] = None
    scanned_for_shelving: Optional[bool] = None
    collection_accessioned: Optional[bool] = None
    collection_verified: Optional[bool] = None
    verification_job_id: Optional[int] = None
    shelving_job_id: Optional[int] = None
    container_type_id: Optional[int] = None
    owner_id: Optional[int] = None
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
                "scanned_for_verification": False,
                "scanned_for_shelving": False,
                "collection_accessioned": False,
                "collection_verified": False,
                "verification_job_id": 1,
                "shelving_job_id": 1,
                "container_type_id": 1,
                "owner_id": 1,
                "media_type_id": 1,
                "conveyance_bin_id": 1,
                "size_class_id": 1,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "accession_dt": "2023-10-08T20:46:56.764426",
                "shelved_dt": "2023-10-08T20:46:56.764426",
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class TrayMoveInput(BaseModel):
    shelf_barcode_value: str
    shelf_position_number: int

    class Config:
        json_schema_extra = {
            "example": {
                "shelf_barcode_value": "5901234123457",
                "shelf_position_number": 1
            }
        }


class TrayUpdateInput(TrayInput):
    shelf_position_id: Optional[int] = None
    shelf_position_proposed_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
                "scanned_for_shelving": False,
                "collection_accessioned": False,
                "collection_verified": False,
                "verification_job_id": 1,
                "shelving_job_id": 1,
                "container_type_id": 1,
                "owner_id": 1,
                "shelf_position_id": 1,
                "shelf_position_proposed_id": 1,
                "media_type_id": 1,
                "conveyance_bin_id": 1,
                "size_class_id": 1,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                "accession_dt": "2023-10-08T20:46:56.764426",
                "shelved_dt": "2023-10-08T20:46:56.764426",
                "withdrawal_dt": "2023-10-08T20:46:56.764426"
            }
        }


class ItemNestedForTrayOutput(BaseModel):
    id: int
    scanned_for_accession: bool
    scanned_for_verification: bool
    barcode: BarcodeDetailReadOutput


class NestedShelfPositionNumber(BaseModel):
    number: int


class ShelfPositionNestedForTrayOutput(BaseModel):
    id: int
    shelf_id: int
    shelf_position_number: NestedShelfPositionNumber
    location: Optional[str] = None
    internal_location: Optional[str] = None


class TrayBaseOutput(TrayInput):
    id: int
    items: List[ItemNestedForTrayOutput]
    barcode: BarcodeDetailReadOutput
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: SizeClassDetailReadOutput
    shelf_position: Optional[ShelfPositionNestedForTrayOutput] = None

class TrayListOutput(TrayBaseOutput):
    owner: Optional[OwnerDetailReadOutput]

    class Config:
        json_schema_extra = {
            "example": [
                {
                    "accession_job_id": 1,
                    "scanned_for_accession": False,
                    "scanned_for_verification": False,
                    "scanned_for_shelving": False,
                    "collection_accessioned": False,
                    "collection_verified": False,
                    "verification_job_id": 1,
                    "shelving_job_id": 1,
                    "container_type_id": 1,
                    "owner_id": 1,
                    "shelf_position_id": 1,
                    "shelf_position_proposed_id": 1,
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
                        "short_name": "CL",
                        "assigned": False,
                        "height": 15.7,
                        "width": 30.33,
                        "depth": 27,
                        "create_dt": "2023-11-27T12:34:56.789123Z",
                        "update_dt": "2023-11-27T12:34:56.789123Z"
                    },
                    "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                    "barcode": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "value": "5901234123457",
                        "type_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "shelf_position": {
                        "id": 1,
                        "shelf_id": 1,
                        "shelf_position_number": {
                            "number": 1
                        }
                    },
                    "accession_dt": "2023-10-08T20:46:56.764426",
                    "shelved_dt": "2023-10-08T20:46:56.764426",
                    "withdrawal_dt": "2023-10-08T20:46:56.764426",
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
            ]
        }


class TrayDetailWriteOutput(TrayBaseOutput):
    owner: Optional[OwnerDetailReadOutput]
    container_type: Optional[ContainerTypeDetailReadOutput]
    shelving_job: Optional[ShelvingJobBaseOutput] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "accession_job_id": 1,
                "scanned_for_accession": False,
                "scanned_for_verification": False,
                "scanned_for_shelving": False,
                "collection_accessioned": False,
                "collection_verified": False,
                "verification_job_id": 1,
                "shelving_job_id": 1,
                "container_type_id": 1,
                "owner_id": 1,
                "shelf_position_id": 1,
                "shelf_position_proposed_id": 1,
                "shelf_position": {
                    "id": 1,
                    "shelf_id": 1,
                    "shelf_position_number": {
                        "number": 1
                    }
                },
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
                "shelving_job": {
                    "id": 1,
                    "status": "Created"
                },
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
                    "short_name": "CL",
                    "assigned": False,
                    "height": 15.7,
                    "width": 30.33,
                    "depth": 27,
                    "create_dt": "2023-11-27T12:34:56.789123Z",
                    "update_dt": "2023-11-27T12:34:56.789123Z"
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
                "scanned_for_verification": False,
                "scanned_for_shelving": False,
                "collection_accessioned": False,
                "collection_verified": False,
                "verification_job_id": 1,
                "shelving_job_id": 1,
                "container_type_id": 1,
                "owner_id": 1,
                "shelf_position_id": 1,
                "shelf_position": {
                    "id": 1,
                    "shelf_id": 1,
                    "location": "Cabin Branch-04-57-L-23-10-08",
                    "internal_location": "01-04-57-L-23-10-08",
                    "shelf_position_number": {
                        "number": 1
                    }
                },
                "shelf_position_proposed_id": 1,
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
                "shelving_job": {
                    "id": 1,
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
                    "short_name": "CL",
                    "assigned": False,
                    "height": 15.7,
                    "width": 30.33,
                    "depth": 27,
                    "create_dt": "2023-11-27T12:34:56.789123Z",
                    "update_dt": "2023-11-27T12:34:56.789123Z"
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
