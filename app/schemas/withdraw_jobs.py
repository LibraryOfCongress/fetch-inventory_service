import uuid

from pydantic import (
    BaseModel,
    field_validator,
    computed_field,
)
from datetime import datetime, timedelta
from typing import Optional, List

from app.models.withdraw_jobs import WithdrawJobStatus
from app.schemas.users import UserDetailReadOutput


class WithdrawJobInput(BaseModel):
    barcode_value: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "barcode_value": "1234567890"
            }
        }


class WithdrawJobUpdateInput(BaseModel):
    create_pick_list: Optional[bool] = None
    add_to_picklist: Optional[bool] = None
    status: Optional[str] = None
    assigned_user_id: Optional[int] = None
    pick_list_id: Optional[int] = None
    run_time: Optional[timedelta] = None
    run_timestamp: Optional[datetime] = None
    last_transition: Optional[datetime] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in WithdrawJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(WithdrawJobStatus._member_names_)}"
            )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "status": "Created",
                "assigned_user_id": 1,
                "pick_list_id": 1,
                "run_time": "00:00:00",
                "last_transition": "2022-01-01 00:00:00",
                "run_timestamp": "2022-01-01 00:00:00",
            }
        }


class PickBaseOutput(BaseModel):
    id: int
    status: str


class ItemBaseOutput(BaseModel):
    id: int
    status: str


class NonTrayItemBaseOutput(BaseModel):
    id: int
    status: str


class TrayItemBaseOutput(BaseModel):
    id: int


class NestedBarcodeTypeOutputForBarcode(BaseModel):
    id: int
    name: str


class BarcodeDetailOutput(BaseModel):
    id: uuid.UUID | None
    value: str
    type_id: int
    type: NestedBarcodeTypeOutputForBarcode
    create_dt: datetime
    update_dt: datetime


class NestedShelfNumberForWithdrawJob(BaseModel):
    number: int


class NestedShelfPositionNumberForWithdrawJob(BaseModel):
    number: int


class NestedShelfForWithdrawJob(BaseModel):
    id: int
    barcode: BarcodeDetailOutput
    shelf_number: NestedShelfNumberForWithdrawJob


class ShelfPositionNestedForWithdrawJob(BaseModel):
    id: int
    shelf_position_number: NestedShelfPositionNumberForWithdrawJob
    shelf: NestedShelfForWithdrawJob


class NestedTrayForWithdrawJob(BaseModel):
    id: int
    barcode: BarcodeDetailOutput
    shelf_position: ShelfPositionNestedForWithdrawJob


class NestedOwnerForWithdrawJob(BaseModel):
    id: int
    name: Optional[str] = None


class ItemNestedForWithdrawJob(BaseModel):
    id: int
    status: str
    barcode: BarcodeDetailOutput
    owner: Optional[NestedOwnerForWithdrawJob] = None
    tray: Optional[NestedTrayForWithdrawJob] = None

    class Config:
        from_attributes = True


class ItemNestedWithoutTrayForWithdrawJob(BaseModel):
    id: int
    status: str
    barcode: BarcodeDetailOutput
    owner: Optional[NestedOwnerForWithdrawJob] = None


class NonTrayNestedForWithdrawJob(BaseModel):
    id: int
    status: str
    barcode: Optional[BarcodeDetailOutput] = None
    owner: Optional[NestedOwnerForWithdrawJob] = None
    shelf_position_id: Optional[int] = None
    shelf_position: Optional[ShelfPositionNestedForWithdrawJob] = None

    class Config:
        from_attributes = True


class TrayNestedForWithdrawJob(BaseModel):
    id: int
    barcode: BarcodeDetailOutput
    owner: Optional[NestedOwnerForWithdrawJob] = None
    shelf_position: Optional[ShelfPositionNestedForWithdrawJob] = None
    items: Optional[List[ItemNestedWithoutTrayForWithdrawJob]] = None

    class Config:
        from_attributes = True


class WithdrawJobBaseOutput(BaseModel):
    id: int
    status: str
    assigned_user_id: Optional[int] = None
    create_dt: datetime
    update_dt: datetime


class WithdrawJobListOutput(WithdrawJobBaseOutput):
    run_time: Optional[timedelta] = None
    run_timestamp: Optional[datetime] = None
    last_transition: Optional[datetime] = None
    assigned_user: Optional[UserDetailReadOutput] = None
    items: Optional[list[ItemBaseOutput]] = None
    non_tray_items: Optional[list[NonTrayItemBaseOutput]] = None
    trays: Optional[list[TrayItemBaseOutput]] = None

    @computed_field(title="Item Count")
    @property
    def item_count(self) -> int:
        return len(self.items)

    @computed_field(title="Non Tray Item Count")
    @property
    def non_tray_item_count(self) -> int:
        return len(self.non_tray_items)

    @computed_field(title="Tray Count")
    @property
    def tray_count(self) -> int:
        return len(self.trays)

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "Created",
                "assigned_user_id": 1,
                "run_time": "00:00:00",
                "run_timestamp": "2022-01-01 00:00:00",
                "last_transition": "2022-01-01 00:00:00",
                "items": {
                    "id": 1
                },
                "non_tray_items": {
                    "id": 1
                },
                "trays": {
                    "id": 1
                },
                "item_count": 1,
                "tray_count": 1,
                "non_tray_item_count": 1,
            }
        }


class WithdrawJobWriteOutput(WithdrawJobBaseOutput):
    items: Optional[list[ItemNestedForWithdrawJob]] = None
    non_tray_items: Optional[list[NonTrayNestedForWithdrawJob]] = None
    trays: Optional[list[TrayNestedForWithdrawJob]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "Created",
                "assigned_user_id": 1,
                "items": [
                    {
                        "id": 1,
                        "status": "Out",
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "type": {
                                "id": 1,
                                "name": "Item"
                            }
                        },
                        "owner": {
                            "id": 1,
                            "name": "Test Owner"
                        },
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764426"
                    }
                ],
                "non_tray_items": [
                    {
                        "id": 1,
                        "status": "Out",
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "type": {
                                "id": 1,
                                "name": "Item"
                            }
                        },
                        "owner": {
                            "id": 1,
                            "name": "Special Collection Directorate"
                        },
                        "shelving_job_id": 1,
                        "shelf_position_id": 1,
                        "shelf_position": {
                            "id": 1,
                            "barcode": {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "value": "5901234123457",
                                "type_id": 1,
                                "type": {
                                    "id": 1,
                                    "name": "Item"
                                }
                            },
                            "shelf_id": 1,
                            "shelf_position_number": {
                                "number": 1
                            }
                        },
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764426"
                    }
                ],
                "tray": [
                    {
                        "id": 1,
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "type": {
                                "id": 1,
                                "name": "Item"
                            }
                        },
                        "owner": {
                            "id": 1,
                            "name": "Special Collection Directorate"
                        },
                        "shelf_position": {
                            "id": 1,
                            "barcode": {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "value": "5901234123457",
                                "type_id": 1,
                                "type": {
                                    "id": 1,
                                    "name": "Item"
                                }
                            },
                            "shelf_id": 1,
                            "shelf_position_number": {
                                "number": 1
                            }
                        },
                        "items": [
                            {
                                "id": 1,
                                "status": "Out",
                                "barcode": {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "value": "5901234123457",
                                    "type_id": 1,
                                    "type": {
                                        "id": 1,
                                        "name": "Item"
                                    }
                                },
                                "owner": {
                                    "id": 1,
                                    "name": "Test Owner"
                                },
                                "create_dt": "2023-10-08T20:46:56.764426",
                                "update_dt": "2023-10-08T20:46:56.764426"
                            }
                        ],
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764426",
            }
        }


class ErrorNestedForWithdrawJob(BaseModel):
    barcode: str
    error: str


class WithdrawJobDetailOutput(WithdrawJobBaseOutput):
    pick_list_id: Optional[int] = None
    run_time: Optional[timedelta] = None
    run_timestamp: Optional[datetime] = None
    last_transition: Optional[datetime] = None
    assigned_user: Optional[UserDetailReadOutput] = None
    items: Optional[list[ItemNestedForWithdrawJob]] = None
    non_tray_items: Optional[list[NonTrayNestedForWithdrawJob]] = None
    trays: Optional[list[TrayNestedForWithdrawJob]] = None
    pick_list: Optional[PickBaseOutput] = None
    errors: Optional[list[ErrorNestedForWithdrawJob]] = None

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

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "Created",
                "assigned_user_id": 1,
                "pick_list_id": 1,
                "run_time": "00:00:00.000000",
                "run_timestamp": "2023-10-08T20:46:56.764426",
                "last_transition": "2023-10-08T20:46:56.764426",
                "items": [
                    {
                        "id": 1,
                        "status": "Out",
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "type": {
                                "id": 1,
                                "name": "Item"
                            }
                        },
                        "owner": {
                            "id": 1,
                            "name": "Test Owner"
                        },
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764426"
                    }
                ],
                "non_tray_items": [
                    {
                        "id": 1,
                        "status": "Out",
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "type": {
                                "id": 1,
                                "name": "Item"
                            }
                        },
                        "owner": {
                            "id": 1,
                            "name": "Special Collection Directorate"
                        },
                        "shelving_job_id": 1,
                        "shelf_position_id": 1,
                        "shelf_position": {
                            "id": 1,
                            "barcode": {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "value": "5901234123457",
                                "type_id": 1,
                                "type": {
                                    "id": 1,
                                    "name": "Item"
                                }
                            },
                            "shelf_id": 1,
                            "shelf_position_number": {
                                "number": 1
                            }
                        },
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764426"
                    }
                ],
                "tray": [
                    {
                        "id": 1,
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "type": {
                                "id": 1,
                                "name": "Item"
                            }
                        },
                        "owner": {
                            "id": 1,
                            "name": "Special Collection Directorate"
                        },
                        "shelf_position": {
                            "id": 1,
                            "barcode": {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "value": "5901234123457",
                                "type_id": 1,
                                "type": {
                                    "id": 1,
                                    "name": "Item"
                                }
                            },
                            "shelf_id": 1,
                            "shelf_position_number": {
                                "number": 1
                            }
                        },
                        "items": [
                            {
                                "id": 1,
                                "status": "Out",
                                "barcode": {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "value": "5901234123457",
                                    "type_id": 1,
                                    "type": {
                                        "id": 1,
                                        "name": "Item"
                                    }
                                },
                                "owner": {
                                    "id": 1,
                                    "name": "Test Owner"
                                },
                                "create_dt": "2023-10-08T20:46:56.764426",
                                "update_dt": "2023-10-08T20:46:56.764426"
                            }
                        ],
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764426"
            }
        }
