# /code/app/schemas/shelving_jobs.py - REFACRORED TO PYDANTIC V2

from pydantic import BaseModel, field_validator, computed_field, Field, ConfigDict
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from app.schemas.users import UserDetailReadOutput
from app.models.shelving_jobs import ShelvingJobStatus, OriginStatus, ShelvingMode
from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput


class ShelvingJobInput(BaseModel):
    """
    Unified input schema for creating shelving jobs.
    
    - origin='Direct': Creates a Direct to Shelf job
    - origin='List': Creates a Shelve by List job (optionally with verification_job_ids)
    """
    origin: str  # Required: "Direct" or "List"
    mode: Optional[str] = "Manual"  # ShelvingMode: "Manual" or "PreAssigned"
    building_id: int  # Required for all job types
    created_by_id: Optional[int] = None
    assigned_user_id: Optional[int] = None  # For job assignment
    # Verification jobs to populate container list (for List origin)
    verification_job_ids: Optional[List[int]] = None
    # Pre-assignment configuration flags
    allow_unassigned_size: Optional[bool] = False
    allow_unassigned_owner: Optional[bool] = False
    allow_tiered_owner: Optional[bool] = False

    @field_validator("origin", mode="before", check_fields=True)
    @classmethod
    def validate_origin(cls, value):
        allowed_origins = ["Direct", "List", "Move"]
        if value not in allowed_origins:
            raise ValueError(
                f"Invalid origin: {value}. Must be one of {allowed_origins}"
            )
        return value

    @field_validator("mode", mode="before", check_fields=True)
    @classmethod
    def validate_mode(cls, value):
        if value is not None and value not in ShelvingMode._member_names_:
            raise ValueError(
                f"Invalid mode: {value}. Must be one of {list(ShelvingMode._member_names_)}"
            )
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin": "Direct",
                "mode": "Manual",
                "building_id": 1,
                "created_by_id": 2,
                "allow_unassigned_size": False,
                "allow_unassigned_owner": False,
                "allow_tiered_owner": False,
                "verification_job_ids": None
            }
        }
    )


class ShelvingJobUpdateInput(BaseModel):
    status: Optional[str] = None
    assigned_user_id: Optional[int] = None
    building_id: Optional[int] = None
    run_timestamp: Optional[datetime] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in ShelvingJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(ShelvingJobStatus._member_names_)}"
            )
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "Created",
                "assigned_user_id": 1,
                "building_id": 1,
                "run_timestamp": "2023-10-08T20:46:56.764426"
            }
        }
    )


class ShelvingJobBaseOutput(BaseModel):
    id: int
    status: Optional[str]
    origin: Optional[str]
    mode: Optional[str] = None  # NEW: ShelvingMode
    building_id: Optional[int] = None
    last_transition: Optional[datetime] = None
    run_time: Optional[timedelta] = None
    assigned_user: Optional[UserDetailReadOutput] = None
    created_by: Optional[UserDetailReadOutput] = None
    # NEW: Pre-assignment configuration flags
    allow_unassigned_size: Optional[bool] = None
    allow_unassigned_owner: Optional[bool] = None
    allow_tiered_owner: Optional[bool] = None
    create_dt: datetime
    update_dt: datetime


class ShelvingJobListOutput(ShelvingJobBaseOutput):
    tray_count: int = 0
    non_tray_item_count: int = 0
    container_count: int = 0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "status": "Created",
                "origin": "Verification",
                "building_id": 1,
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
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "tray_count": 10,
                "non_tray_item_count": 5,
                "container_count": 15
            }
        }
    )


class VerificationJobNestedForShelvingJob(BaseModel):
    id: int
    trayed: bool


class NestedShelfPositionNumberForShelvingJob(BaseModel):
    number: int


class NestedBuildingForShelvingJob(BaseModel):
    id: int
    name: Optional[str] = None


class NestedShelfForShelvingJob(BaseModel):
    id: int
    barcode: Optional[BarcodeDetailReadOutput] = None


class ShelfPositionNestedForShelvingJob(BaseModel):
    id: int
    position_number: int
    shelf: NestedShelfForShelvingJob
    location: Optional[str] = None
    internal_location: Optional[str] = None


class NestedOwnerForShelvingJob(BaseModel):
    id: int
    name: Optional[str] = None


class NestedSizeClassForShelvingJob(BaseModel):
    id: int
    name: str
    short_name: str


class TrayNestedForShelvingJob(BaseModel):
    id: int
    owner: Optional[NestedOwnerForShelvingJob] = None
    size_class: Optional[NestedSizeClassForShelvingJob] = None
    shelf_position_id: Optional[int] = None
    shelf_position: Optional[ShelfPositionNestedForShelvingJob] = None
    shelf_position_proposed_id: Optional[int] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    withdrawn_barcode: Optional[BarcodeDetailReadOutput] = None
    container_type: Optional[ContainerTypeDetailReadOutput]
    scanned_for_shelving: Optional[bool] = None


class ItemNestedForShelvingJob(BaseModel):
    id: int
    barcode: Optional[BarcodeDetailReadOutput] = None
    tray: Optional[TrayNestedForShelvingJob] = None
    scanned_for_accession: bool
    scanned_for_verification: bool
    status: str


class NonTrayNestedForShelvingJob(BaseModel):

    id: int
    owner: Optional[NestedOwnerForShelvingJob] = None
    size_class: Optional[NestedSizeClassForShelvingJob] = None
    shelf_position_id: Optional[int] = None
    shelf_position: Optional[ShelfPositionNestedForShelvingJob] = None
    shelf_position_proposed_id: Optional[int] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    withdrawn_barcode: Optional[BarcodeDetailReadOutput] = None
    container_type: Optional[ContainerTypeDetailReadOutput]
    scanned_for_shelving: Optional[bool] = None



class ShelvingJobContainerDetailOutput(BaseModel):
    id: int
    shelving_job_id: int
    tray: Optional[TrayNestedForShelvingJob] = None
    non_tray_item: Optional[NonTrayNestedForShelvingJob] = None
    item: Optional[ItemNestedForShelvingJob] = None
    destination_tray: Optional[TrayNestedForShelvingJob] = None

    proposed_shelf_position: Optional[ShelfPositionNestedForShelvingJob] = None
    actual_shelf_position: Optional[ShelfPositionNestedForShelvingJob] = None
    shelved_dt: Optional[datetime] = None
    status: str
    was_overridden: bool = False
    
    @computed_field(title='Container Barcode')
    @property
    def container_barcode(self) -> Optional[str]:
        if self.tray:
            return self.tray.barcode.value if self.tray.barcode else f"TRAY-{self.tray.id}"
        if self.non_tray_item:
            return self.non_tray_item.barcode.value if self.non_tray_item.barcode else f"NTI-{self.non_tray_item.id}"
        if self.item:
            return self.item.barcode.value if self.item.barcode else f"ITEM-{self.item.id}"
        return None

    @computed_field(title='Shelf Position Number')
    @property
    def shelf_position_number(self) -> Optional[int]:
        if self.actual_shelf_position:
            return self.actual_shelf_position.position_number
        if self.proposed_shelf_position:
            return self.proposed_shelf_position.position_number
        return None

class ShelvingJobDetailOutput(ShelvingJobBaseOutput):
    assigned_user_id: Optional[int] = None
    created_by_id: Optional[int] = None
    verification_jobs: Optional[List[VerificationJobNestedForShelvingJob]] = []
    trays: List[TrayNestedForShelvingJob]
    non_tray_items: List[NonTrayNestedForShelvingJob]
    building: Optional[NestedBuildingForShelvingJob] = None
    shelving_job_containers: List[ShelvingJobContainerDetailOutput] = []


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
                "status": "Created",
                "origin": "Verification",
                "building_id": 1,
                "building": {
                    "id": 1,
                    "name": "Fort Meade"
                },
                "assigned_user_id": 1,
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
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "verification_jobs": [
                    {
                        "id": 1,
                        "trayed": True
                    }
                ],
                "trays": [
                    {
                        "id": 1,
                        "owner": {
                            "id": 1,
                            "name": "Library Of Congress"
                        },
                        "size_class": {
                            "id": 1,
                            "name": "Record Storage",
                            "short_name": "RS"
                        },
                        "shelf_position_id": 1,
                        "shelf_position_proposed_id": 1,
                        "scanned_for_shelving": False,
                        "container_type": {
                            "id": 1,
                            "type": "Tray",
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "shelf_position": {
                            "id": 1,
                            "position_number": 5,
                            "location": "Cabin Branch-04-57-L-23-10-08",
                            "internal_location": "01-04-57-L-23-10-08",
                            "shelf": {
                                "id": 1,
                                "shelf_number": 1,
                                "barcode": {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "value": "5901234123457",
                                    "type_id": 1,
                                    "type": {
                                        "id": 1,
                                        "name": "Item"
                                    },
                                    "create_dt": "2023-10-08T20:46:56.764426",
                                    "update_dt": "2023-10-08T20:46:56.764398"
                                },
                            }
                        }
                    }
                ],
                "non_tray_items": [
                    {
                        "id": 1,
                        "owner": {
                            "id": 1,
                            "name": "Library Of Congress"
                        },
                        "size_class": {
                            "id": 1,
                            "name": "Record Storage",
                            "short_name": "RS"
                        },
                        "shelf_position_id": 1,
                        "shelf_position_proposed_id": 1,
                        "scanned_for_shelving": False,
                        "container_type": {
                            "id": 2,
                            "type": "Non-Tray",
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "shelf_position": {
                            "id": 1,
                            "position_number": 5,
                            "shelf": {
                                "id": 1,
                                "shelf_number": 1,
                                "barcode": {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "value": "5901234123457",
                                    "type_id": 1,
                                    "type": {
                                        "id": 1,
                                        "name": "Item"
                                    },
                                    "create_dt": "2023-10-08T20:46:56.764426",
                                    "update_dt": "2023-10-08T20:46:56.764398"
                                },
                            }
                        }
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
    )


class ReAssignmentInput(BaseModel):
    """
    Custom input with no underlying model.
    """
    container_id: Optional[int] = None
    container_barcode_value: Optional[str] = None
    trayed: Optional[bool] = None
    destination_tray_id: Optional[int] = None
    destination_tray_barcode_value: Optional[str] = None
    shelf_position_number: Optional[int] = None
    shelf_id: Optional[int] = None
    shelf_barcode_value: Optional[str] = None
    shelved_dt: Optional[datetime] = None
    scanned_for_shelving: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "container_id": 1,
            "container_barcode_value": "yx233lnb",
            "trayed": True,
            "shelf_position_number": 5,
            "shelf_id": 1,
            "shelf_barcode_value": "xy332bnl",
            "shelved_dt": "2023-10-08T20:46:56.764426",
            "scanned_for_shelving": True
        }
    )


class ReAssignmentOutput(BaseModel):
    """
    Designed to be container agnostic,
    returns Tray or NonTrayItem data.
    """
    id: int
    shelving_job_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    shelf_position_proposed_id: Optional[int] = None
    scanned_for_shelving: Optional[bool] = None
    barcode: BarcodeDetailReadOutput
    owner: Optional[NestedOwnerForShelvingJob] = None
    size_class: Optional[NestedSizeClassForShelvingJob] = None
    shelf_position: Optional[ShelfPositionNestedForShelvingJob] = None
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    next_available_position: Optional[int] = None
    shelving_container_id: Optional[int] = None  # Unified container tracking ID

    model_config = ConfigDict(
        json_schema_extra={
            "id": 1,
            "shelving_job_id": 1,
            "shelf_position_id": 242,
            "shelf_position_proposed_id": 200,
            "scanned_for_shelving": True,
            "barcode": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "value": "5901234123457",
                "type_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            },
            "owner": {
                "id": 1,
                "name": "Library Of Congress"
            },
            "size_class": {
                "id": 1,
                "name": "Record Storage",
                "short_name": "RS"
            },
            "container_type": {
                "id": 2,
                "type": "Non-Tray",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            },
            "shelf_position": {
                "id": 1,
                "position_number": 5,
                "shelf": {
                                "id": 1,
                                "ladder": {
                                    "id": 1,
                                    "ladder_number": 1,
                                    "side": {
                                        "id": 1,
                                        "side_orientation": {
                                            "name": "Left"
                                        },
                                        "aisle": {
                                            "id": 1,
                                            "aisle_number": 1,
                                            "module": {
                                                "id": 1,
                                                "module_number": "1"
                                            },
                                            "building": {
                                                "id": 1,
                                                "name": "Cabin Branch"
                                            }
                                        }
                                    }
                                },
                                "shelf_number": 1,
                                "barcode": {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "value": "5901234123457",
                                    "type_id": 1,
                                    "type": {
                                        "id": 1,
                                        "name": "Item"
                                    },
                                    "create_dt": "2023-10-08T20:46:56.764426",
                                    "update_dt": "2023-10-08T20:46:56.764398"
                                },
                            }
            }
        }
    )


class ProposedReAssignmentInput(BaseModel):
    """
    Custom input with no underlying model.
    """
    container_id: Optional[int] = None
    container_barcode_value: Optional[str] = None
    shelf_id: Optional[int] = None
    shelf_position_number: int
    shelf_barcode_value: Optional[str] = None