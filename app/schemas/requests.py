import uuid

from typing import Optional, List
from pydantic import BaseModel, conint
from datetime import datetime

from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.buildings import BuildingDetailReadOutput


class RequestInput(BaseModel):
    building_id: Optional[int] = None
    request_type_id: Optional[int] = None
    item_id: Optional[int] = None
    non_tray_item_id: Optional[int] = None
    delivery_location_id: Optional[int] = None
    priority_id: Optional[int] = None
    external_request_id: Optional[str] = None
    requestor_name: Optional[str] = None
    barcode_value: str  # pop this off in path operations

    class Config:
        json_schema_extra = {
            "example": {
                "building_id": 1,
                "barcode_value": "RS4321",
                "request_type_id": 1,
                "item_id": 1,
                "non_tray_item_id": 1,
                "delivery_location_id": 1,
                "priority_id": 1,
                "requestor_name": "Bilbo Baggins",
                "external_request_id": "12345",
            }
        }


class RequestUpdateInput(BaseModel):
    building_id: Optional[int] = None
    request_type_id: Optional[int] = None
    item_id: Optional[int] = None
    non_tray_item_id: Optional[int] = None
    delivery_location_id: Optional[int] = None
    priority_id: Optional[int] = None
    external_request_id: Optional[str] = None
    batch_upload_id: Optional[int] = None
    requestor_name: Optional[str] = None
    barcode_value: Optional[str] = None  # pop this off in path operations
    scanned_for_retrieval: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "building_id": 1,
                "barcode_value": "RS4321",
                "request_type_id": 1,
                "item_id": 1,
                "non_tray_item_id": None,
                "delivery_location_id": 1,
                "priority_id": 1,
                "batch_upload_id": 1,
                "requestor_name": "Bilbo Baggins",
                "external_request_id": "12345",
                "scanned_for_pick_list": False,
                "scanned_for_retrieval": False
            }
        }


class RequestBaseOutput(BaseModel):
    id: int
    building_id: Optional[int] = None
    request_type_id: Optional[int] = None
    item_id: Optional[int] = None
    non_tray_item_id: Optional[int] = None
    delivery_location_id: Optional[int] = None
    priority_id: Optional[int] = None
    external_request_id: Optional[str] = None
    batch_upload_id: Optional[int] = None
    requestor_name: Optional[str] = None
    scanned_for_pick_list: Optional[bool] = None
    scanned_for_retrieval: Optional[bool] = None


class MediaTypeNestedForRequest(BaseModel):
    id: int
    name: str


class ShelfPositionNumberNestedForRequest(BaseModel):
    number: int


class AisleNumberNestedForRequest(BaseModel):
    number: int


class NestedBuildingRequestModule(BaseModel):
    id: int
    name: Optional[str] = None


class ModuleNestedForRequest(BaseModel):
    id: int
    module_number: str
    building: Optional[NestedBuildingRequestModule] = None


class BuildingNestedForRequest(BaseModel):
    id: int
    name: Optional[str] = None


class ShelfNestedForRequest(BaseModel):
    id: int
    # barcode: Optional[BarcodeDetailReadOutput] = None


class ShelfPositionNestedForRequest(BaseModel):
    id: int
    shelf_id: int
    shelf_position_number: ShelfPositionNumberNestedForRequest
    shelf: Optional[ShelfNestedForRequest] = None
    location: Optional[str] = None
    internal_location: Optional[str] = None


class TrayNestedForRequest(BaseModel):
    id: int
    barcode: Optional[BarcodeDetailReadOutput] = None
    shelf_position: Optional[ShelfPositionNestedForRequest] = None


class NestedSizeClassForRequest(BaseModel):
    id: int
    name: Optional[str] = None
    short_name: Optional[str] = None


class NestedOwnerForRequest(BaseModel):
    id: int
    name: Optional[str] = None


class ItemNestedForRequest(BaseModel):
    id: int
    title: Optional[str] = None
    volume: Optional[str] = None
    condition: Optional[str] = None
    size_class: Optional[NestedSizeClassForRequest] = None
    owner: Optional[NestedOwnerForRequest] = None
    accession_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    status: Optional[str] = None
    media_type: Optional[MediaTypeNestedForRequest] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    tray: Optional[TrayNestedForRequest] = None


class NonTrayItemNestedForRequest(BaseModel):
    id: int
    status: Optional[str] = None
    media_type: Optional[MediaTypeNestedForRequest] = None
    size_class: Optional[NestedSizeClassForRequest] = None
    owner: Optional[NestedOwnerForRequest] = None
    accession_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    shelf_position: Optional[ShelfPositionNestedForRequest] = None


class PriorityNestedForRequest(BaseModel):
    id: int
    value: str


class DeliveryLocationNestedForRequest(BaseModel):
    id: int
    name: Optional[str] = None
    address: str


class RequestTypeNestedForRequest(BaseModel):
    id: int
    type: str


class NestedPickListForRequest(BaseModel):
    id: int
    created_by_id: Optional[int] = None
    status: Optional[str] = None
    building_id: Optional[int] = None
    update_dt: Optional[datetime] = None
    create_dt: Optional[datetime] = None


class RequestDetailWriteOutput(RequestBaseOutput):
    item: Optional[ItemNestedForRequest] = None
    non_tray_item: Optional[NonTrayItemNestedForRequest] = None
    priority: Optional[PriorityNestedForRequest] = None
    delivery_location: Optional[DeliveryLocationNestedForRequest] = None
    request_type: Optional[RequestTypeNestedForRequest] = None
    building: Optional[BuildingDetailReadOutput] = None
    pick_list_id: Optional[int] = None
    pick_list: Optional[NestedPickListForRequest] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "building_id": 1,
                "request_type_id": 1,
                "item_id": 1,
                "non_tray_item_id": None,
                "delivery_location_id": 1,
                "priority_id": 1,
                "batch_upload_id": 1,
                "priority": {
                    "id": 1,
                    "value": "Medium"
                },
                "request_type": {
                    "id": 1,
                    "type": "General Delivery"
                },
                "delivery_location": {
                    "name": "Senator McSenator",
                    "address": "1234 Example St, Washington D.C 12345",
                },
                "item": {
                    "id": 1,
                    "title": "Grapes of Wrath",
                    "volume": "1",
                    "condition": "Do not serve (it's boring)",
                    "size_class": {
                        "id": 1,
                        "name": "Record Storage",
                        "short_name": "RS",
                    },
                    "owner": {
                        "id": 1,
                        "name": "CMD"
                    },
                    "accession_dt": "2023-10-08T20:46:56.764426",
                    "withdrawal_dt": "2023-10-08T20:46:56.764426",
                    "status": "In",
                    "media_type": {
                        "id": 1,
                        "name": "Book"
                    },
                    "barcode": {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "value": "5901234123457",
                        "type_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398",
                    },
                    "tray": {
                        "id": 1,
                        "barcode": {
                            "id": "255fer-e29b-41d4-a716-446655440001",
                            "value": "3301234123457",
                            "type_id": 1,
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398",
                        },
                        "shelf_position": {
                            "id": 1,
                            "shelf_id": 1,
                            "shelf": {
                                "id": 1,
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
                            "shelf_position_number": {
                                "number": 1
                            },
                        },
                    },
                },
                "pick_list": {
                    "id": 1,
                    "user_id": 1,
                    "status": "Created"
                },
                "non_tray_item": None,
                "requestor_name": "Bilbo Baggins",
                "external_request_id": "12345",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }


# Some redundant nested classes solve circular resolution


class NestedBarcodeRequestList(BaseModel):
    id: uuid.UUID | None
    value: str
    type_id: int
    create_dt: datetime
    update_dt: datetime


class NestedTrayRequestList(BaseModel):
    id: int
    barcode: Optional[NestedBarcodeRequestList] = None
    shelf_position: Optional[ShelfPositionNestedForRequest] = None


class NestedItemRequestList(BaseModel):
    id: int
    title: Optional[str] = None
    volume: Optional[str] = None
    condition: Optional[str] = None
    size_class: Optional[NestedSizeClassForRequest] = None
    owner: Optional[NestedOwnerForRequest] = None
    accession_dt: Optional[datetime] = None
    withdrawal_dt: Optional[datetime] = None
    status: Optional[str] = None
    media_type: Optional[MediaTypeNestedForRequest] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    tray: Optional[NestedTrayRequestList] = None


class RequestListOutput(RequestBaseOutput):
    pick_list_id: Optional[int] = None
    item: Optional[NestedItemRequestList] = None
    non_tray_item: Optional[NonTrayItemNestedForRequest] = None
    priority: Optional[PriorityNestedForRequest] = None
    delivery_location: Optional[DeliveryLocationNestedForRequest] = None
    request_type: Optional[RequestTypeNestedForRequest] = None
    building: Optional[BuildingDetailReadOutput] = None
    pick_list: Optional[NestedPickListForRequest] = None
    create_dt: Optional[datetime] = None
    update_dt: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "building_id": 1,
                "request_type_id": 1,
                "item_id": 1,
                "non_tray_item_id": None,
                "delivery_location_id": 1,
                "priority_id": 1,
                "batch_upload_id": 1,
                "priority": {
                    "id": 1,
                    "value": "Medium"
                },
                "request_type": {
                    "id": 1,
                    "type": "General Delivery"
                },
                "delivery_location": {
                    "name": "Senator McSenator",
                    "address": "1234 Example St, Washington D.C 12345"
                },
                "item": {
                    "id": 1,
                    "title": "Grapes of Wrath",
                    "volume": "1",
                    "condition": "Do not serve (it's boring)",
                    "size_class": {
                        "id": 1,
                        "name": "Record Storage",
                        "short_name": "RS"
                    },
                    "owner": {
                        "id": 1,
                        "name": "CMD"
                    },
                    "accession_dt": "2023-10-08T20:46:56.764426",
                    "withdrawal_dt": "2023-10-08T20:46:56.764426",
                    "status": "In",
                    "media_type": {
                        "id": 1,
                        "name": "Book"
                    },
                    "barcode": {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "value": "5901234123457",
                        "type_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "tray": {
                        "id": 1,
                        "barcode": {
                            "id": "255fer-e29b-41d4-a716-446655440001",
                            "value": "3301234123457",
                            "type_id": 1,
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "shelf_position": {
                            "id": 1,
                            "shelf_id": 1,
                            "shelf": {
                                "id": 1,
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
                            "shelf_position_number": {
                                "number": 2
                            },
                        },
                    },
                },
                "pick_list": {
                    "id": 1,
                    "user_id": 1,
                    "status": "Created"
                },
                "non_tray_item": None,
                "requestor_name": "Bilbo Baggins",
                "external_request_id": "12345",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class RequestDetailReadOutput(RequestDetailWriteOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "building_id": 1,
                "request_type_id": 1,
                "item_id": 1,
                "non_tray_item_id": None,
                "delivery_location_id": 1,
                "priority_id": 1,
                "batch_upload_id": 1,
                "priority": {
                    "id": 1,
                    "value": "Medium"
                },
                "request_type": {
                    "id": 1,
                    "type": "General Delivery"
                },
                "delivery_location": {
                    "name": "Senator McSenator",
                    "address": "1234 Example St, Washington D.C 12345"
                },
                "item": {
                    "id": 1,
                    "title": "Grapes of Wrath",
                    "volume": "1",
                    "condition": "Do not serve (it's boring)",
                    "size_class": {
                        "id": 1,
                        "name": "Record Storage",
                        "short_name": "RS"
                    },
                    "owner": {
                        "id": 1,
                        "name": "CMD"
                    },
                    "accession_dt": "2023-10-08T20:46:56.764426",
                    "withdrawal_dt": "2023-10-08T20:46:56.764426",
                    "status": "In",
                    "media_type": {
                        "id": 1,
                        "name": "Book"
                    },
                    "barcode": {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "value": "5901234123457",
                        "type_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "tray": {
                        "id": 1,
                        "barcode": {
                            "id": "255fer-e29b-41d4-a716-446655440001",
                            "value": "3301234123457",
                            "type_id": 1,
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "shelf_position": {
                            "id": 1,
                            "shelf_id": 1,
                            "shelf": {
                                "id": 1,
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
                            "shelf_position_number": {
                                "number": 2
                            }
                        }
                    }
                },
                "pick_list": {
                    "id": 1,
                    "user_id": 1,
                    "status": "Created"
                },
                "non_tray_item": None,
                "requestor_name": "Bilbo Baggins",
                "external_request_id": "12345",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class RequestDetailReadOutputNoPickList(RequestBaseOutput):
    item: Optional[NestedItemRequestList] = None
    non_tray_item: Optional[NonTrayItemNestedForRequest] = None
    priority: Optional[PriorityNestedForRequest] = None
    delivery_location: Optional[DeliveryLocationNestedForRequest] = None
    request_type: Optional[RequestTypeNestedForRequest] = None
    building: Optional[BuildingDetailReadOutput] = None
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "building_id": 1,
                "request_type_id": 1,
                "item_id": 1,
                "non_tray_item_id": None,
                "delivery_location_id": 1,
                "priority_id": 1,
                "batch_upload_id": 1,
                "priority": {
                    "id": 1,
                    "value": "Medium"
                },
                "request_type": {
                    "id": 1,
                    "type": "General Delivery"
                },
                "building": {
                    "id": 1,
                    "name": "Southpoint Circle"
                },
                "delivery_location": {
                    "name": "Senator McSenator",
                    "address": "1234 Example St, Washington D.C 12345"
                },
                "item": {
                    "id": 1,
                    "title": "Grapes of Wrath",
                    "volume": "1",
                    "condition": "Do not serve (it's boring)",
                    "size_class": {
                        "id": 1,
                        "name": "Record Storage",
                        "short_name": "RS"
                    },
                    "owner": {
                        "id": 1,
                        "name": "CMD"
                    },
                    "accession_dt": "2023-10-08T20:46:56.764426",
                    "withdrawal_dt": "2023-10-08T20:46:56.764426",
                    "status": "In",
                    "media_type": {
                        "id": 1,
                        "name": "Book"
                    },
                    "barcode": {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "value": "5901234123457",
                        "type_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "tray": {
                        "id": 1,
                        "barcode": {
                            "id": "255fer-e29b-41d4-a716-446655440001",
                            "value": "3301234123457",
                            "type_id": 1,
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "shelf_position": {
                            "id": 1,
                            "shelf_id": 1,
                            "shelf": {
                                "id": 1,
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
                            "shelf_position_number": {
                                "number": 2
                            },
                        },
                    },
                },
                "non_tray_item": None,
                "requestor_name": "Bilbo Baggins",
                "external_request_id": "12345",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
