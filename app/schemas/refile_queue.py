from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput


class RefileQueueInput(BaseModel):
    barcode_value: str

    class Config:
        json_schema_extra = {
            "example": {
                "barcode_value": "1234567890"
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
    module_number: str
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
                "module_number": "1",
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


class NestedShelfForRefileQueue(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput
    shelf_number: NestedShelfNumberForRefileQueue


class ShelfPositionNestedForRefileQueue(BaseModel):
    id: int
    shelf_position_number: NestedShelfPositionNumberForRefileQueue
    shelf: NestedShelfForRefileQueue
    location: Optional[str] = None
    internal_location: Optional[str] = None


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
    item: Optional[TrayNestedForRefileQueue] = None
    non_tray_item: Optional[NonTrayNestedForRefileQueue] = None

    class Config:
        json_schema_extra = {
            "example": {
                "items": {
                    "id": 1,
                    "status": "Out",
                    "owner": {
                        "id": 1,
                        "name": "Bruce Wayne"
                    },
                    "size_class": {
                        "id": 1,
                        "name": "C High",
                        "short_name": "C"
                    },
                    "tray": {
                        "id": 1,
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "type": {
                                "id": 1,
                                "name": "Item"
                            },
                        },
                        "shelf_position": {
                            "id": 1,
                            "shelf_position_number": {
                                "number": 1
                            },
                            "shelf": {
                                "id": 1,
                                "shelf_number": {
                                    "number": 1
                                },
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
                            },
                            "location": "Cabin Branch-04-57-L-23-10-08",
                            "internal_location": "01-04-57-L-23-10-08",
                        }
                    },
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
                    "container_type": {
                        "id": 1,
                        "type": "Tray",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "scanned_for_shelving": True
                },
                "non_tray_items": {
                    "id": 1,
                    "status": "Out",
                    "owner": {
                        "id": 1,
                        "name": "Bruce Wayne"
                    },
                    "size_class": {
                        "id": 1,
                        "name": "C High",
                        "short_name": "C"
                    },
                    "shelf_position_id": 1,
                    "shelf_position": {
                        "id": 1,
                        "shelf_position_number": {
                            "number": 1
                        },
                        "shelf": {
                            "id": 1,
                            "shelf_number": {
                                "number": 1
                            },
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
                        },
                        "location": "Cabin Branch-04-57-L-23-10-08",
                        "internal_location": "01-04-57-L-23-10-08"
                    },
                    "shelf_position_proposed_id": 1,
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
                    "container_type": {
                        "id": 1,
                        "type": "Tray",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "scanned_for_shelving": True
                }
            }
        }
