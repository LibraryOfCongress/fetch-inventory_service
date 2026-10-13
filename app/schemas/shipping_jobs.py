
from pydantic import BaseModel, Field, ConfigDict, computed_field, field_validator
from typing import Optional, List
from datetime import datetime, timedelta
from app.schemas.users import UserDetailReadOutput
from app.models.shipping_jobs import ShippingJobStatus
from app.models.shipping_bins import ShippingBinStatus
from app.schemas.barcodes import BarcodeDetailReadOutput

# --- Nested Schemas ---

class ItemNestedForShipping(BaseModel):
    id: int
    barcode: Optional[BarcodeDetailReadOutput] = None
    title: Optional[str] = None
    call_number: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)

class DeliveryLocationNestedForShipping(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class NonTrayItemNestedForShipping(ItemNestedForShipping):
    pass


class ShippingItemCheckOutput(BaseModel):
    delivery_location_id: int
    delivery_location: Optional[DeliveryLocationNestedForShipping] = None
    request_id: Optional[int] = None
    item_id: Optional[int] = None
    non_tray_item_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class ShippingBinDetailOutput(BaseModel):
    id: int
    shipping_job_id: int
    barcode: str
    status: str
    delivery_location_id: Optional[int] = None
    delivery_location: Optional[DeliveryLocationNestedForShipping] = None
    cleared_dt: Optional[datetime] = None
    cleared_by_id: Optional[int] = None
    cleared_by: Optional[UserDetailReadOutput] = None
    create_dt: datetime
    update_dt: datetime
    items: List[ItemNestedForShipping] = []
    non_tray_items: List[NonTrayItemNestedForShipping] = []

    @computed_field
    def item_count(self) -> int:
        return len(self.items) + len(self.non_tray_items)

    model_config = ConfigDict(from_attributes=True)

# --- Job Schemas ---

class ShippingJobInput(BaseModel):
    assigned_user_id: Optional[int] = None

class ShippingJobUpdateInput(BaseModel):
    status: Optional[str] = None
    assigned_user_id: Optional[int] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v and v not in ShippingJobStatus._member_names_:
             raise ValueError(f"Invalid status: {v}")
        return v

class ShippingJobOutput(BaseModel):
    id: int
    status: str
    assigned_user_id: Optional[int] = None
    assigned_user: Optional[UserDetailReadOutput] = None
    created_by_id: Optional[int] = None
    created_by: Optional[UserDetailReadOutput] = None

    create_dt: datetime
    update_dt: datetime
    completed_dt: Optional[datetime] = None
    last_transition: Optional[datetime] = None
    run_time: Optional[timedelta] = None

    bins: List[ShippingBinDetailOutput] = []

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

    @computed_field
    def bin_count(self) -> int:
        return len(self.bins)

    @computed_field
    def total_items(self) -> int:
        return sum(len(b.items) + len(b.non_tray_items) for b in self.bins)

    model_config = ConfigDict(from_attributes=True)

class ShippingJobListOutput(ShippingJobOutput):
    # Simplified output for lists if needed, but for now reuse detail
    # We might exclude nested items in lists for performance, but stick to simple for now
    pass
