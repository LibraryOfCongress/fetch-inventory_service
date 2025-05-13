from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone

from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.size_class import SizeClassDetailReadOutput


class AccessionItemsDetailOutput(BaseModel):
    year: Optional[str] = "All"
    month: Optional[str] = "All"
    owner_name: Optional[str] = "All"
    size_class_name: Optional[str] = "All"
    media_type_name: Optional[str] = "All"
    count: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "owner_name": "All",
                "size_class_name": "All",
                "media_type_name": "All",
                "year": 2025,
                "month": "Jan",
                "count": 100,
            }
        }


class ShelvingJobDiscrepancyBaseOutput(BaseModel):
    id: int
    shelving_job_id: int
    tray_id: Optional[int] = None
    non_tray_item_id: Optional[int] = None
    user_id: Optional[int] = None
    owner_id: Optional[int] = None
    size_class_id: Optional[int] = None
    assigned_location: Optional[str] = None
    pre_assigned_location: Optional[str] = None
    error: Optional[str] = None
    create_dt: datetime
    update_dt: datetime


class NestedUserSJobDiscrepancy(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


class NestedTraySJobDiscrepancy(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput


class NestedNonTrayItemSJobDiscrepancy(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput


class NestedOwnerSJobDiscrepancy(BaseModel):
    id: int
    name: Optional[str] = None


class NestedSizeClassSJobDiscrepancy(BaseModel):
    id: int
    short_name: Optional[str] = None


class ShelvingJobDiscrepancyOutput(ShelvingJobDiscrepancyBaseOutput):
    assigned_user: Optional[NestedUserSJobDiscrepancy] = None
    tray: Optional[NestedTraySJobDiscrepancy] = None
    non_tray_item: Optional[NestedNonTrayItemSJobDiscrepancy] = None
    owner: Optional[NestedOwnerSJobDiscrepancy] = None
    size_class: Optional[NestedSizeClassSJobDiscrepancy] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "shelving_job_id": 1,
                "tray_id": 1,
                "non_tray_item_id": None,
                "user_id": 1,
                "owner_id": 1,
                "size_class_id": 1,
                "error": "Location Discrepancy - Position or Shelf does not match Job assignment.",
                "assigned_user": {
                    "first_name": "Bilbo",
                    "last_name": "Baggins",
                    "email": "bbaggins@bagend.hobbit",
                },
                "tray": {
                    "id": 1,
                    "barcode": {
                        "id": "0031dbfb-28d3-496f-91d3-8e16d9bdbd16",
                        "value": "12345",
                    },
                },
                "non_tray_item": "",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


class NestedBarcodeOpenLocations(BaseModel):
    value: Optional[str] = None


class NestedSizeClassOpenLocations(BaseModel):
    short_name: str


class NestedShelfTypeOpenLocations(BaseModel):
    id: int
    size_class: Optional[NestedSizeClassOpenLocations] = None
    max_capacity: int


class NestedOwnerOpenLocations(BaseModel):
    id: int
    name: Optional[str] = None


class OpenLocationsOutput(BaseModel):
    barcode: Optional[NestedBarcodeOpenLocations] = None
    location: Optional[str] = None
    internal_location: Optional[str] = None
    available_space: int
    owner: Optional[NestedOwnerOpenLocations] = None
    height: Optional[float] = None
    width: Optional[float] = None
    depth: Optional[float] = None
    shelf_type: Optional[NestedShelfTypeOpenLocations] = None


class AisleDetailReportItemCountOutput(BaseModel):
    aisle_id: int
    aisle_number: int
    shelf_count: Optional[int] = 0
    item_count: Optional[int] = 0
    non_tray_item_count: Optional[int] = 0
    tray_count: Optional[int] = 0
    total_item_count: Optional[int] = 0

    class Config:
        json_schema_extra = {
            "example": {
                "aisle_id": 1,
                "aisle_number": 1,
                "shelf_count": 1,
                "item_count": 1,
                "non_tray_item_count": 1,
                "tray_count": 1,
                "total_item_count": 1,
            }
        }


class NonTrayItemCountReadOutput(BaseModel):
    size_class_id: int
    size_class_name: Optional[str] = "All"
    size_class_short_name: Optional[str] = "All"
    non_tray_item_count: Optional[int] = 0

    class Config:
        json_schema_extra = {
            "example": {
                "size_class_id": 1,
                "size_class_name": "C-Low",
                "size_class_short_name": "CL",
                "non_tray_item_count": 1,
            }
        }


class TrayItemCountReadOutput(BaseModel):
    size_class_id: int
    size_class_name: Optional[str] = "All"
    size_class_short_name: Optional[str] = "All"
    tray_count: Optional[int] = 0
    tray_item_count: Optional[int] = 0

    class Config:
        json_schema_extra = {
            "example": {
                "size_class_id": 1,
                "size_class_name": "C-Low",
                "size_class_short_name": "CL",
                "tray_count": 1,
                "tray_item_count": 1,
            }
        }


class UserJobItemCountReadOutput(BaseModel):
    user_name: Optional[str] = "All"
    job_type: str
    total_items_processed: Optional[int] = 0

    class Config:
        json_schema_extra = {
            "example": {
                "user_name": "Bilbo Baggins",
                "job_type": "Shelving",
                "total_items_processed": 1,
            }
        }


class VerificationChangesOutput(BaseModel):
    workflow_id: int
    completed_dt: datetime
    completed_by: str
    tray_barcode: Optional[str] = None
    item_barcode: Optional[str] = None
    action: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": 1,
                "completed_dt": "2023-10-08T20:46:56.764426",
                "completed_by": "Bilbo Baggins",
                "tray_barcode_value": "12345",
                "item_barcode_value": "12345",
                "action": "Added",
            }
        }


class RetrievalItemCountReadOutput(BaseModel):
    owner_name: str
    total_item_retrieved_count: Optional[int] = 0
    max_retrieved_count: Optional[int] = 0

    class Config:
        json_schema_extra = {
            "example": {
                "owner_name": "Bilbo Baggins",
                "total_item_retrieved_count": 1,
                "max_retrieved_count": 1,
            }
        }


class MoveDiscrepancyBaseOutput(BaseModel):
    id: int
    tray_id: Optional[int] = None
    non_tray_item_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    owner_id: Optional[int] = None
    size_class_id: Optional[int] = None
    container_type_id: Optional[int] = None
    original_assigned_location: Optional[str] = None
    current_assigned_location: Optional[str] = None
    error: Optional[str] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "tray_id": 1,
                "non_tray_item_id": 1,
                "assigned_user_id": 1,
                "owner_id": 1,
                "size_class_id": 1,
                "container_type_id": 1,
                "original_assigned_location": "Fort Meade-1-1-L-27-1-8",
                "current_assigned_location": "Fort Meade-1-1-L-28-1-8",
                "error": "Not Shelved Discrepancy - Container barcode 12345678901 is "
                         "not in a Shelf",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764426",
            }
        }


class NestedUserMoveDiscrepancy(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


class NestedTrayMoveDiscrepancy(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput


class NestedItemMoveDiscrepancy(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput


class NestedNonTrayItemMoveDiscrepancy(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput


class NestedOwnerMoveDiscrepancy(BaseModel):
    id: int
    name: Optional[str] = None


class NestedSizeClassMoveDiscrepancy(BaseModel):
    id: int
    short_name: Optional[str] = None


class MoveDiscrepancyOutput(MoveDiscrepancyBaseOutput):
    assigned_user: Optional[NestedUserMoveDiscrepancy] = None
    item: Optional[NestedItemMoveDiscrepancy] = None
    tray: Optional[NestedTrayMoveDiscrepancy] = None
    non_tray_item: Optional[NestedNonTrayItemMoveDiscrepancy] = None
    owner: Optional[NestedOwnerMoveDiscrepancy] = None
    size_class: Optional[NestedSizeClassMoveDiscrepancy] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "tray_id": 1,
                "non_tray_item_id": 1,
                "assigned_user_id": 1,
                "owner_id": 1,
                "size_class_id": 1,
                "container_type_id": 1,
                "original_assigned_location": "Fort Meade-1-1-L-27-1-8",
                "current_assigned_location": "Fort Meade-1-1-L-28-1-8",
                "error": "Not Shelved Discrepancy - Container barcode 12345678901 is "
                         "not in a Shelf",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764426",
                "assigned_user": {
                    "id": 1,
                    "first_name": "Bilbo",
                    "last_name": "Baggins",
                    "email": "bbaggins@bagend.hobbit",
                },
                "tray": {
                    "id": 1,
                    "barcode": {
                        "id": "0031dbfb-28d3-496f-91d3-8e16d9bdbd16",
                        "value": "12345",
                    },
                },
                "item": {
                    "id": 1,
                    "barcode": {
                        "id": "0031dbfb-28d3-496f-91d3-8e16d9bdbd16",
                        "value": "12345",
                    },
                    "tray": {
                        "id": 1,
                        "barcode": {
                            "id": "0031dbfb-28d3-496f-91d3-8e16d9bdbd16",
                            "value": "12345",
                        },
                    },
                },
                "non_tray_item": {
                    "id": 1,
                    "barcode": {
                        "id": "0031dbfb-28d3-496f-91d3-8e16d9bdbd16",
                        "value": "12345",
                    },
                },
            }
        }
