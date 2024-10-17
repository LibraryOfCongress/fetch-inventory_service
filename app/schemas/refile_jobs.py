from typing import Optional
from pydantic import BaseModel, field_validator, computed_field
from datetime import timedelta, datetime

from app.models.refile_jobs import RefileJobStatus
from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput
from app.schemas.users import UserDetailReadOutput


class RefileJobInput(BaseModel):
    barcode_values: list[str]

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


class RefileJobUpdateInput(BaseModel):
    assigned_user_id: Optional[int] = None
    run_timestamp: Optional[datetime] = None
    status: Optional[str] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in RefileJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(RefileJobStatus._member_names_)}"
            )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "assigned_user_id": 1,
                "run_timestamp": "2023-11-27T12:34:56.789123Z",
                "status": "Created"
            }
        }


class RefileJobBaseOutput(BaseModel):
    id: int
    assigned_user_id: Optional[int] = None
    status: Optional[str] = None
    run_time: Optional[timedelta] = None
    last_transition: Optional[datetime] = None
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

    @computed_field(title='Item Count')
    @property
    def item_count(self) -> int:
        if self.items is None:
            return 0
        return len(self.items)

    @computed_field(title='Item filed Count')
    @property
    def item_shelved_refiled_count(self) -> int:
        count = 0
        if self.items is None:
            return count
        for item in self.items:
            if item.status == "In":
                count += 1
        return count

    @computed_field(title='NonTray Count')
    @property
    def non_tray_item_count(self) -> int:
        if self.non_tray_items is None:
            return 0
        return len(self.non_tray_items)

    @computed_field(title='Non Tray Item filed Count')
    @property
    def non_tray_item_shelved_refiled_count(self) -> int:
        count = 0
        if self.non_tray_items is None:
            return count
        for non_tray_item in self.non_tray_items:
            if non_tray_item.status == "In":
                count += 1
        return count

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "assigned_user_id": 1,
                "status": "Created",
                "run_time": "03:25:15",
                "last_transition": "2023-10-08T20:46:56.764426Z",
                "item_count": 1,
                "item_shelved_refiled_count": 1,
                "non_tray_item_count": 1,
                "non_tray_item_shelved_refiled_count": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764426"
            }
        }


class RefileJobListOutput(RefileJobBaseOutput):
    assigned_user: Optional[UserDetailReadOutput] = None
    items: Optional[list] = None
    non_tray_items: Optional[list] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "assigned_user_id": 1,
                "assigned_user": {
                    "id": 1,
                    "first_name": "Frodo",
                    "last_name": "Baggins",
                    "email": "FBaggins@example.com",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "run_time": "03:25:15",
                "status": "Created",
                "items": [
                    {
                        "id": 1,
                        "status": "In",
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
                        "withdrawal_dt": "2023-10-08T20:46:56.764426",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                ],
                "non_tray_items": [
                    {
                        "id": 1,
                        "status": "In",
                        "accession_job_id": 1,
                        "scanned_for_accession": False,
                        "scanned_for_verification": False,
                        "scanned_for_shelving": False,
                        "verification_job_id": 1,
                        "shelving_job_id": 1,
                        "shelf_position_id": 1,
                        "shelf_position_proposed_id": 1,
                        "container_type_id": 2,
                        "owner_id": 1,
                        "subcollection_id": 1,
                        "media_type_id": 1,
                        "size_class_id": 1,
                        "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
                        "accession_dt": "2023-10-08T20:46:56.764426",
                        "withdrawal_dt": "2023-10-08T20:46:56.764426",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                ],
                "item_count": 1,
                "item_shelved_refiled_count": 1,
                "non_tray_item_count": 1,
                "non_tray_item_shelved_refiled_count": 1
            }
        }


class NestedShelfNumberForRefileJob(BaseModel):
    number: int


class NestedShelfPositionNumberForRefileJob(BaseModel):
    number: int


class NestedLadderNumberForRefileJob(BaseModel):
    number: int


class NestedSideOrientationForRefileJob(BaseModel):
    name: str


class NestedAisleNumberForRefileJob(BaseModel):
    number: int


class NestedModuleForRefileJob(BaseModel):
    id: int
    module_number: str


class NestedBuildingForRefileJob(BaseModel):
    id: int
    name: str

class NestedAisleForRefileJob(BaseModel):
    id: int
    aisle_number: NestedAisleNumberForRefileJob
    module: Optional[NestedModuleForRefileJob] = None
    building: Optional[NestedBuildingForRefileJob] = None


class NestedSideForRefileJob(BaseModel):
    id: int
    side_orientation: NestedSideOrientationForRefileJob
    aisle: NestedAisleForRefileJob


class NestedLadderForRefileJob(BaseModel):
    id: int
    ladder_number: NestedLadderNumberForRefileJob
    side: NestedSideForRefileJob


class NestedShelfForRefileJob(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput
    ladder: NestedLadderForRefileJob
    shelf_number: NestedShelfNumberForRefileJob


class ShelfPositionNestedForRefileJob(BaseModel):
    id: int
    shelf_position_number: NestedShelfPositionNumberForRefileJob
    shelf: NestedShelfForRefileJob
    location: Optional[str] = None
    internal_location: Optional[str] = None


class NestedTrayForRefileJob(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput
    shelf_position: ShelfPositionNestedForRefileJob


class NestedOwnerForRefileJob(BaseModel):
    id: int
    name: Optional[str] = None


class NestedSizeClassForRefileJob(BaseModel):
    id: int
    name: str
    short_name: str


class TrayNestedForRefileJob(BaseModel):
    id: int
    status: str
    owner: Optional[NestedOwnerForRefileJob] = None
    size_class: Optional[NestedSizeClassForRefileJob] = None
    tray: Optional[NestedTrayForRefileJob] = None
    barcode: BarcodeDetailReadOutput
    container_type: Optional[ContainerTypeDetailReadOutput]
    scanned_for_shelving: Optional[bool] = None


class NonTrayNestedForRefileJob(BaseModel):
    id: int
    status: str
    owner: Optional[NestedOwnerForRefileJob] = None
    size_class: Optional[NestedSizeClassForRefileJob] = None
    shelf_position_id: Optional[int] = None
    shelf_position: Optional[ShelfPositionNestedForRefileJob] = None
    shelf_position_proposed_id: Optional[int] = None
    barcode: BarcodeDetailReadOutput
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    scanned_for_shelving: Optional[bool] = None


class NestedForRefileJob(BaseModel):
    id: int
    status: str
    owner: Optional[NestedOwnerForRefileJob] = None
    size_class: Optional[NestedSizeClassForRefileJob] = None
    tray: Optional[NestedTrayForRefileJob] = None
    shelf_position_id: Optional[int] = None
    shelf_position: Optional[ShelfPositionNestedForRefileJob] = None
    shelf_position_proposed_id: Optional[int] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    scanned_for_shelving: Optional[bool] = None


class RefileJobDetailOutput(RefileJobBaseOutput):
    assigned_user: Optional[UserDetailReadOutput] = None
    items: Optional[list[TrayNestedForRefileJob]] = None
    non_tray_items: Optional[list[NonTrayNestedForRefileJob]] = None
    refile_job_items: Optional[list[NestedForRefileJob]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "assigned_user_id": 1,
                "run_time": "03:25:15",
                "status": "Created",
                "create_dt": "2023-11-27T12:34:56.789123Z",
                "update_dt": "2023-11-27T12:34:56.789123Z",
                "assigned_user": {
                    "id": 1,
                    "first_name": "Frodo",
                    "last_name": "Baggins",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "items": [
                    {
                        "id": 1,
                        "status": "In",
                        "owner": {
                            "id": 1,
                            "name": "Special Collection Directorate"
                        },
                        "size_class": {
                            "id": 1,
                            "name": "C-Low",
                            "short_name": "CL"
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
                                "create_dt": "2023-10-08T20:46:56.764426",
                                "update_dt": "2023-10-08T20:46:56.764398"
                            },
                            "shelf_position": {
                                "location": "Cabin Branch-04-57-L-23-10-08",
                                "internal_location": "01-04-57-L-23-10-08",
                                "shelf_position_number": {
                                    "number": 1
                                },
                                "shelf": {
                                    "id": 1,
                                    "ladder": {
                                        "id": 1,
                                        "ladder_number": {
                                            "number": 1
                                        },
                                        "side": {
                                            "id": 1,
                                            "side_orientation": {
                                                "name": "Left"
                                            },
                                            "aisle": {
                                                "id": 1,
                                                "aisle_number": {
                                                    "number": 1
                                                },
                                                "module": {
                                                    "id": 1,
                                                    "module_number": "1"
                                                },
                                                "building": {
                                                    "id": 1,
                                                    "name": "Cabin Branch"
                                                }
                                            }
                                        }
                                    },
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
                                }
                            }
                        },
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440001",
                            "value": "5901234123457",
                            "type_id": 1,
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
                ],
                "non_tray_items": [
                    {
                        "id": 1,
                        "status": "In",
                        "owner": {
                            "id": 1,
                            "name": "Special Collection Directorate"
                        },
                        "size_class": {
                            "id": 1,
                            "name": "C-Low",
                            "short_name": "CL"
                        },
                        "shelf_position_id": 1,
                        "shelf_position": {
                            "location": "Cabin Branch-04-57-L-23-10-08",
                            "internal_location": "01-04-57-L-23-10-08",
                            "shelf_position_number": {
                                "number": 1
                            },
                            "shelf": {
                                "id": 1,
                                "ladder": {
                                    "id": 1,
                                    "ladder_number": {
                                        "number": 1
                                    },
                                    "side": {
                                        "id": 1,
                                        "side_orientation": {
                                            "name": "Left"
                                        },
                                        "aisle": {
                                            "id": 1,
                                            "aisle_number": {
                                                "number": 1
                                            },
                                            "module": {
                                                "id": 1,
                                                "module_number": "1"
                                            },
                                            "building": {
                                                "id": 1,
                                                "name": "Cabin Branch"
                                            }
                                        }
                                    }
                                },
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
                        },
                        "shelf_position_proposed_id": 1,
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440001",
                            "value": "5901234123457",
                            "type_id": 1,
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
                ],
                "refile_job_items": [
                    {
                        "id": 1,
                        "status": "In",
                        "owner": {
                            "id": 1,
                            "name": "Special Collection Directorate"
                        },
                        "size_class": {
                            "id": 1,
                            "name": "C-Low",
                            "short_name": "CL"
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
                                "create_dt": "2023-10-08T20:46:56.764426",
                                "update_dt": "2023-10-08T20:46:56.764398"
                            },
                            "shelf_position": {
                                "location": "Cabin Branch-04-57-L-23-10-08",
                                "internal_location": "01-04-57-L-23-10-08",
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
                                }
                            }
                        },
                        "shelf_position_id": 1,
                        "shelf_position": {
                            "location": "Cabin Branch-04-57-L-23-10-08",
                            "internal_location": "01-04-57-L-23-10-08",
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
                            }
                        },
                        "shelf_position_proposed_id": 1,
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440001",
                            "value": "5901234123457",
                            "type_id": 1,
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
                ],
                "item_count": 1,
                "item_shelved_refiled_count": 1,
                "non_tray_item_count": 1,
                "non_tray_item_shelved_refiled_count": 1
            }
        }
