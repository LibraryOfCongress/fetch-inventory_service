from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.schemas.barcodes import BarcodeDetailReadOutput


class AccessionItemsDetailOutput(BaseModel):
    owner_name: Optional[str] = "All"
    size_class_name: Optional[str] = "All"
    media_type_name: Optional[str] = "All"
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "owner_name": "All",
                "size_class_name": "All",
                "media_type_name": "All",
                "count": 1
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
                    "email": "bbaggins@bagend.hobbit"
                },
                "tray": {
                    "id": 1,
                    "barcode": {
                        "id": "0031dbfb-28d3-496f-91d3-8e16d9bdbd16",
                        "value": "12345"
                    }
                },
                "non_tray_item": "",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
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

