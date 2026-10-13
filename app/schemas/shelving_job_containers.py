# /code/app/schemas/shelving_job_containers.py - NEW SCHEMA FOR SHELVE BY LIST FEATURE

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ShelvingJobContainerInput(BaseModel):
    """Input for adding a container to a shelving job list."""
    container_barcode: str  # Can be tray or non-tray item barcode

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_barcode": "TRAY00123"
            }
        }
    )


class ShelvingJobContainerOverrideInput(BaseModel):
    """Input for overriding a container's proposed location."""
    shelf_barcode: Optional[str] = None
    shelf_position_id: Optional[int] = None
    shelf_position_number: Optional[int] = None
    reason: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shelf_barcode": "SHELF-B1-M2-A3-L5-S3",
                "shelf_position_number": 2,
                "reason": "User Override"
            }
        }
    )


class NestedBarcodeForContainer(BaseModel):
    """Simplified barcode info for container output."""
    id: str
    value: str
    type_id: Optional[int] = None


class NestedOwnerForContainer(BaseModel):
    id: int
    name: Optional[str] = None


class NestedSizeClassForContainer(BaseModel):
    id: int
    name: str
    short_name: str


class NestedShelfPositionForContainer(BaseModel):
    id: int
    location: Optional[str] = None


class ShelvingJobContainerOutput(BaseModel):
    """Output for a container in a shelving job list."""
    id: int
    shelving_job_id: int
    tray_id: Optional[int] = None
    non_tray_item_id: Optional[int] = None
    
    # Container details (populated from relationship)
    barcode: Optional[NestedBarcodeForContainer] = None
    owner: Optional[NestedOwnerForContainer] = None
    size_class: Optional[NestedSizeClassForContainer] = None
    container_type: Optional[str] = None  # "Tray" or "Non-Tray"
    
    # Pre-assignment tracking
    proposed_shelf_position_id: Optional[int] = None
    proposed_location: Optional[str] = None  # Computed from position
    position_reserved_at: Optional[datetime] = None
    
    # Actual result
    actual_shelf_position_id: Optional[int] = None
    actual_location: Optional[str] = None  # Computed from position
    shelved_dt: Optional[datetime] = None
    
    # Override tracking
    was_overridden: bool = False
    override_reason: Optional[str] = None
    
    # Status
    status: str
    error_message: Optional[str] = None
    
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "shelving_job_id": 42,
                "tray_id": 123,
                "non_tray_item_id": None,
                "barcode": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "value": "TRAY00123",
                    "type_id": 1
                },
                "owner": {
                    "id": 1,
                    "name": "Library of Congress"
                },
                "size_class": {
                    "id": 1,
                    "name": "Record Storage",
                    "short_name": "RS"
                },
                "container_type": "Tray",
                "proposed_shelf_position_id": 456,
                "proposed_location": "B1-M2-A3-L-5-3-1",
                "position_reserved_at": "2026-01-16T18:10:00Z",
                "actual_shelf_position_id": None,
                "actual_location": None,
                "shelved_dt": None,
                "was_overridden": False,
                "override_reason": None,
                "status": "Assigned",
                "error_message": None,
                "create_dt": "2026-01-16T18:10:00Z",
                "update_dt": "2026-01-16T18:10:00Z"
            }
        }
    )


class PreAssignmentInput(BaseModel):
    """Input for running pre-assignment on a shelving job."""
    building_id: int
    module_id: Optional[int] = None
    aisle_id: Optional[int] = None
    ladder_id: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "building_id": 1,
                "module_id": 2,
                "aisle_id": None,
                "ladder_id": None
            }
        }
    )


class PreAssignmentResult(BaseModel):
    """Result of running pre-assignment."""
    assigned_count: int
    unassigned_count: int
    unassigned_barcodes: list[str]
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "assigned_count": 85,
                "unassigned_count": 15,
                "unassigned_barcodes": ["TRAY00456", "TRAY00457"],
                "message": "85 of 100 containers assigned. 15 could not be assigned due to insufficient matching shelf positions."
            }
        }
    )


class ShelveByListJobInput(BaseModel):
    """Input for creating a new Shelve by List job."""
    building_id: int
    mode: str  # "Manual" or "PreAssigned"
    verification_job_ids: Optional[list[int]] = None
    allow_unassigned_size: bool = False
    allow_unassigned_owner: bool = False
    allow_tiered_owner: bool = False
    created_by_id: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "building_id": 1,
                "mode": "PreAssigned",
                "verification_job_ids": [101, 102],
                "allow_unassigned_size": False,
                "allow_unassigned_owner": False,
                "allow_tiered_owner": True,
                "created_by_id": 5
            }
        }
    )


class OfflineShelveConfirmation(BaseModel):
    """Input for confirming a shelve action (supports offline sync)."""
    container_id: int
    shelf_barcode: Optional[str] = None  # Scanned shelf barcode for validation
    shelf_position_id: Optional[int] = None  # Or direct position ID
    override: bool = False
    override_reason: Optional[str] = None
    timestamp: Optional[datetime] = None  # When the action was performed offline

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": 123,
                "shelf_barcode": "SHELF-B1-M2-A3-L5-S3",
                "shelf_position_id": None,
                "override": False,
                "override_reason": None,
                "timestamp": "2026-01-16T18:15:00Z"
            }
        }
    )
