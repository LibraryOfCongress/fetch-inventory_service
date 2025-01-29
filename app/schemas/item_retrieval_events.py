from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.items import ItemDetailReadOutput
from app.schemas.pick_lists import PickListDetailOutput


class ItemRetrievalEventInput(BaseModel):
    item_id: int = None
    owner_id: Optional[int] = None
    pick_list_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "item_id": 1,
                "owner_id": 1,
                "pick_list_id": 1,
            }
        }


class ItemRetrievalEventUpdateInput(BaseModel):
    item_id: Optional[int] = None
    owner_id: Optional[int] = None
    pick_list_id: Optional[int] = None
    update_dt: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "item_id": 1,
                "owner_id": 1,
                "pick_list_id": 1,
                "update_dt": "2023-11-27T12:34:56.789123Z"
            }
        }


class ItemRetrievalEventBaseOutput(BaseModel):
    id: int
    item_id: int = None
    owner_id: Optional[int] = None
    pick_list_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "item_id": 1,
                "owner_id": 1,
                "pick_list_id": 1
            }
        }


class ItemRetrievalEventListOutput(ItemRetrievalEventBaseOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "item_id": 1,
                "owner_id": 1,
                "pick_list_id": 1
            }
        }


class ItemRetrievalEventDetailOutput(ItemRetrievalEventBaseOutput):
    create_dt: Optional[datetime] = None
    update_dt: Optional[datetime] = None
    item: Optional[ItemDetailReadOutput] = None
    owner: Optional[OwnerDetailReadOutput] = None
    pick_list: Optional[PickListDetailOutput] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "item_id": 1,
                "owner_id": 1,
                "pick_list_id": 1,
                "create_dt": "2023-11-27T12:34:56.789123Z",
                "update_dt": "2023-11-27T12:34:56.789123Z",
                "item": {
                    "id": 1,
                    "status": "In",
                    "last_requested_dt": "2023-10-08T20:46:56.764426",
                    "last_refiled_dt": "2023-10-08T20:46:56.764426",
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
                    "barcode": {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "value": "5901234123457",
                        "type_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "withdrawn_barcode": {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "value": "5901234123457",
                        "type_id": 1,
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
                        "height": 15.7,
                        "width": 30.33,
                        "depth": 27,
                        "create_dt": "2023-11-27T12:34:56.789123Z",
                        "update_dt": "2023-11-27T12:34:56.789123Z"
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
                    "owner": {
                        "id": 1,
                        "name": "Special Collection Directorate",
                        "owner_tier_id": 2,
                        "owner_tier": {
                            "id": 1,
                            "level": 2,
                            "name": "division",
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "subcollection": {
                        "id": 1,
                        "name": "A Song of Ice and Fire",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "accession_dt": "2023-10-08T20:46:56.764426",
                    "withdrawal_dt": "2023-10-08T20:46:56.764426",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
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
                    "size_classes": [
                        {
                            "id": 1,
                            "name": "C-Low",
                            "short_name": "CL",
                            "height": 15.7,
                            "width": 30.33,
                            "depth": 27
                        }
                    ],
                    "children": [],
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "pick_list": {
                    "id": 1,
                    "status": "Created",
                    "request_count": 1,
                    "user_id": 1,
                    "created_by_id": 2,
                    "user": {
                        "id": 1,
                        "name": "Bilbo Baggins",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764426"
                    },
                    "created_by": {
                        "id": 2,
                        "name": "Frodo Baggins",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764426"
                    },
                    "requests": [{
                        "id": 1,
                        "item_id": 1,
                        "delivery_location_id": 1,
                        "priority_id": 1,
                        "pick_list_id": 1,
                        "scanned_for_pick_list": False,
                        "requestor_name": "Bilbo Baggins",
                        "request_type_id": 1,
                        "non_tray_item_id": None,
                        "external_request_id": "12345",
                        "create_dt": "2024-05-15T18:13:31.525080",
                        "update_dt": "2024-05-15T18:13:31.525091",
                        "...": "..."
                    }],
                    "building_id": 1,
                    "building": {
                        "id": 1,
                        "name": "Main"
                    },
                    "last_transition": "2023-11-27T12:34:56.789123Z",
                    "run_time": "03:25:15",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764426",
                    "errored_request_ids": [4, 5, 6]
                }
            }
        }
