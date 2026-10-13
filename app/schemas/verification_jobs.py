# /code/app/schemas/verification_jobs.py - FINAL FIX (Strict Types + Reordering)

import uuid

from pydantic import BaseModel, field_validator, computed_field, ConfigDict
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from app.models.verification_jobs import VerificationJobStatus
from app.schemas.accession_jobs import AccessionJobDetailOutput
from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput
from app.schemas.shelving_jobs import ShelvingJobDetailOutput
from app.schemas.media_types import MediaTypeDetailReadOutput
from app.schemas.size_class import SizeClassDetailReadOutput
from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.users import UserDetailReadOutput


# --- INPUT SCHEMAS ---

class VerificationJobInput(BaseModel):
    trayed: bool
    workflow_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None
    status: Optional[str] = None
    assigned_user_id: Optional[int] = None
    created_by_id: Optional[int] = None
    accession_job_id: Optional[int] = None
    owner_id: int
    container_type_id: Optional[int] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in VerificationJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(VerificationJobStatus._member_names_)}"
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
                "accession_job_id": 1,
                "owner_id": 1,
                "container_type_id": 1,
                "media_type_id": 1,
                "size_class_id": 1
            }
        }
    )


class VerificationJobUpdateInput(BaseModel):
    trayed: Optional[bool] = None
    status: Optional[str] = None
    assigned_user_id: Optional[int] = None
    accession_job_id: Optional[int] = None
    owner_id: Optional[int] = None
    container_type_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in VerificationJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(VerificationJobStatus._member_names_)}"
            )
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trayed": True,
                "status": "Created",
                "assigned_user_id": 1,
                "accession_job_id": 1,
                "owner_id": 1,
                "container_type_id": 1,
                "media_type_id": 1,
                "size_class_id": 1
            }
        }
    )


class VerificationJobAddInput(BaseModel):
    user_id: int
    barcode_value: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "barcode_value": "1234567890"
            }
        }
    )


class VerificationJobRemoveInput(VerificationJobAddInput):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "barcode_value": "1234567890"
            }
        }
    )


class VerificationJobBaseOutput(BaseModel):
    id: int
    workflow_id: Optional[int] = None
    trayed: bool
    status: Optional[str]
    owner_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None
    update_dt: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# --- NESTED SCHEMAS (Moved up so ListOutput can use them) ---

class NestedWithdrawnBarcode(BaseModel):
    id: uuid.UUID | None
    value: str
    withdrawn: bool
    type_id: int
    model_config = ConfigDict(from_attributes=True)


class ItemDetailNestedForVerificationJob(BaseModel):
    id: int
    status: Optional[str] = None
    ils_sync_state: Optional[str] = None
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
    barcode: Optional[BarcodeDetailReadOutput] = None
    withdrawn_barcode: Optional[BarcodeDetailReadOutput] = None
    
    model_config = ConfigDict(from_attributes=True)


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
    shelving_job_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    shelf_position_proposed_id: Optional[int] = None
    media_type_id: Optional[int] = None
    conveyance_bin_id: Optional[int] = None
    size_class_id: Optional[int] = None
    barcode_id: Optional[uuid.UUID] = None
    accession_dt: Optional[datetime] = None
    shelved_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    withdrawn_barcode: Optional[BarcodeDetailReadOutput] = None
    
    model_config = ConfigDict(from_attributes=True)


class NonTrayItemDetailNestedForVerificationJob(BaseModel):
    id: int
    status: Optional[str] = None
    ils_sync_state: Optional[str] = None
    accession_job_id: Optional[int] = None
    scanned_for_accession: Optional[bool] = None
    scanned_for_verification: Optional[bool] = None
    verification_job_id: Optional[int] = None
    container_type_id: Optional[int] = None
    shelving_job_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    shelf_position_proposed_id: Optional[int] = None
    owner_id: Optional[int] = None
    subcollection_id: Optional[int] = None
    media_type_id: Optional[int] = None
    size_class_id: Optional[int] = None
    barcode_id: Optional[uuid.UUID] = None
    accession_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    media_type: Optional[MediaTypeDetailReadOutput] = None
    size_class: Optional[SizeClassDetailReadOutput] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    withdrawn_barcode: Optional[BarcodeDetailReadOutput] = None

    model_config = ConfigDict(from_attributes=True)


# --- OUTPUT SCHEMAS ---

class VerificationJobListOutput(VerificationJobBaseOutput):
    shelving_job_id: Optional[int] = None
    container_type_id: Optional[int] = None
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    
    assigned_user_id: Optional[int] = None
    created_by_id: Optional[int] = None
    assigned_user: Optional[UserDetailReadOutput] = None
    created_by: Optional[UserDetailReadOutput] = None
    create_dt: datetime
    # NOTE: tray_count / item_count / non_tray_item_count are intentionally NOT
    # exposed here. They map to hybrid properties on VerificationJob whose
    # instance side (len(self.trays), len(self.items) + len(self.non_tray_items))
    # lazy-loads every related row per job — an N+1 that loads full Tray/Item
    # objects just to count them. The dashboard list does not use these counts,
    # so omitting them avoids that load entirely. (The /dropdown endpoint that
    # does need counts computes them SQL-side, not via these properties.)


class VerificationJobListDropdownOutput(BaseModel):
    """
    Lightweight list view for serving minimal job data as options
    """
    id: int
    workflow_id: Optional[int] = None
    trayed: bool
    tray_count: int
    item_count: int
    non_tray_item_count: int
    
    model_config = ConfigDict(from_attributes=True)


class VerificationJobDetailOutput(VerificationJobBaseOutput):
    assigned_user_id: Optional[int] = None
    created_by_id: Optional[int] = None
    assigned_user: Optional[UserDetailReadOutput] = None
    created_by: Optional[UserDetailReadOutput] = None
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
    
    # Typed lists
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
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            # ...
        }
    )


class VerificationJobAccCheckOutput(BaseModel):
    id: int
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1
            }
        }
    )
