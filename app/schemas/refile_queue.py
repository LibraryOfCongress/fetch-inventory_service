from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput


class RefileQueueInput(BaseModel):
    barcode_values: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "barcode_values": [
                    "1234567890",
                    "1234567891",
                    "1234567892",
                    "..."
                ]
            }
        }


class RefileQueueListOutput(BaseModel):
    id: int
    shelf_position_id: int
    shelf_position_number: int
    shelf_id: int
    shelf_number: int
    ladder_id: int
    ladder_number: int
    side_id: int
    side_orientation: str
    aisle_id: int
    aisle_number: int
    module_id: int
    module_number: int
    container_type: str
    media_type: str
    barcode_value: str
    owner: str
    size_class: str
    scanned_for_refile_queue: Optional[bool] = None
    scanned_for_refile_queue_dt: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "shelf_position_id": 1,
                "shelf_position_number": 1,
                "shelf_id": 1,
                "shelf_number": 1,
                "ladder_id": 1,
                "ladder_number": 1,
                "side_id": 1,
                "side_orientation": "Top",
                "aisle_id": 1,
                "aisle_number": 1,
                "module_id": 1,
                "module_number": 1,
                "container_type": "Tray",
                "media_type": "Film",
                "barcode_value": "123456789",
                "owner": "Bruce Wayne",
                "size_class": "C High",
                "scanned_for_refile_queue": True,
                "scanned_for_refile_queue_dt": "2023-10-08T20:46:56.764426"
            }
        }


class NestedShelfNumberForRefileQueue(BaseModel):
    number: int


class NestedShelfPositionNumberForRefileQueue(BaseModel):
    number: int


class NestedLadderNumberForRefileQueue(BaseModel):
    number: int


class NestedSideOrientationForRefileQueue(BaseModel):
    name: str


class NestedAisleNumberForRefileQueue(BaseModel):
    number: int


class NestedModuleNumberForRefileQueue(BaseModel):
    number: int


class NestedModuleForRefileQueue(BaseModel):
    id: int
    module_number: NestedModuleNumberForRefileQueue


class NestedBuildingForRefileQueue(BaseModel):
    id: int
    name: str


class NestedAisleForRefileQueue(BaseModel):
    id: int
    aisle_number: NestedAisleNumberForRefileQueue
    module: Optional[NestedModuleForRefileQueue] = None
    building: Optional[NestedBuildingForRefileQueue] = None


class NestedSideForRefileQueue(BaseModel):
    id: int
    side_orientation: NestedSideOrientationForRefileQueue
    aisle: NestedAisleForRefileQueue


class NestedLadderForRefileQueue(BaseModel):
    id: int
    ladder_number: NestedLadderNumberForRefileQueue
    side: NestedSideForRefileQueue


class NestedShelfForRefileQueue(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput
    ladder: NestedLadderForRefileQueue
    shelf_number: NestedShelfNumberForRefileQueue


class ShelfPositionNestedForRefileQueue(BaseModel):
    id: int
    shelf_position_number: NestedShelfPositionNumberForRefileQueue
    shelf: NestedShelfForRefileQueue


class NestedTrayForRefileQueue(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput
    shelf_position: ShelfPositionNestedForRefileQueue


class NestedOwnerForRefileQueue(BaseModel):
    id: int
    name: Optional[str] = None


class NestedSizeClassForRefileQueue(BaseModel):
    id: int
    name: str
    short_name: str


class TrayNestedForRefileQueue(BaseModel):
    id: int
    status: str
    owner: Optional[NestedOwnerForRefileQueue] = None
    size_class: Optional[NestedSizeClassForRefileQueue] = None
    tray: Optional[NestedTrayForRefileQueue] = None
    barcode: BarcodeDetailReadOutput
    container_type: Optional[ContainerTypeDetailReadOutput]
    scanned_for_shelving: Optional[bool] = None

    class Config:
        from_attributes = True


class NonTrayNestedForRefileQueue(BaseModel):
    id: int
    status: str
    owner: Optional[NestedOwnerForRefileQueue] = None
    size_class: Optional[NestedSizeClassForRefileQueue] = None
    shelf_position_id: Optional[int] = None
    shelf_position: Optional[ShelfPositionNestedForRefileQueue] = None
    shelf_position_proposed_id: Optional[int] = None
    barcode: BarcodeDetailReadOutput
    container_type: Optional[ContainerTypeDetailReadOutput]
    scanned_for_shelving: Optional[bool] = None

    class Config:
        from_attributes = True


class RefileQueueWriteOutput(BaseModel):
    items: Optional[list[TrayNestedForRefileQueue]] = None
    non_tray_items: Optional[list[NonTrayNestedForRefileQueue]] = None
    errored_barcodes: Optional[list] = None

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "status": "Out",
                        "accession_job_id": 1,
                        "scanned_for_accession": False,
                        "scanned_for_verification": False,
                        "verification_job_id": 1,
                        "container_type_id": 1,
                        "tray_id": 1,
                        "owner_id": 1,
                        "title": "Lord of The Rings",
                        "volume": "I",
                        "condition": "Good",
                        "arbitrary_data": "Signed copy",
                        "subcollection_id": 1,
                        "media_type_id": 1,
                        "size_class_id": 1,
                        "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                        "accession_dt": "2023-10-08T20:46:56.764426",
                        "withdrawal_dt": "2023-10-08T20:46:56.764426"
                    }
                ],
                "non_tray_items": [
                    {
                        "id": 1,
                        "status": "Out",
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
                            },
                        },
                        "shelf_position_proposed_id": 1,
                        "container_type_id": 1,
                        "owner_id": 1,
                        "subcollection_id": 1,
                        "media_type_id": 1,
                        "size_class_id": 1,
                        "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                        "accession_dt": "2023-10-08T20:46:56.764426",
                        "withdrawal_dt": "2023-10-08T20:46:56.764426",
                    }
                ],
                "errored_barcodes": [
                    "1234567890",
                    "1234567891",
                    "1234567892",
                    "..."
                ],
            }
        }
