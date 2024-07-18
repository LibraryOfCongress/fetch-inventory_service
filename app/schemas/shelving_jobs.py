from pydantic import BaseModel, field_validator, computed_field
from sqlmodel import Field
from datetime import datetime, timedelta
from typing import Optional, List

from app.schemas.users import UserDetailReadOutput
from app.models.shelving_jobs import ShelvingJobStatus, OriginStatus
from app.schemas.barcodes import BarcodeDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput


class ShelvingJobInput(BaseModel):
    status: Optional[str]
    origin: Optional[str]
    user_id: Optional[int] = None
    building_id: Optional[int] = None
    verification_jobs: Optional[List[int]] = []

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in ShelvingJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(ShelvingJobStatus._member_names_)}"
            )
        return value

    @field_validator("origin", mode="before", check_fields=True)
    @classmethod
    def validate_origin_status(cls, value):
        if value is not None and value not in OriginStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(OriginStatus._member_names_)}"
            )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "status": "Created",
                "origin": "Verification",
                "user_id": 1,
                "building_id": 1,
                "verification_jobs": [
                    1,
                    27,
                    73
                ]
            }
        }


class ShelvingJobUpdateInput(BaseModel):
    status: Optional[str] = None
    user_id: Optional[int] = None
    building_id: Optional[int] = None

    @field_validator("status", mode="before", check_fields=True)
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in ShelvingJobStatus._member_names_:
            raise ValueError(
                f"Invalid status: {value}. Must be one of {list(ShelvingJobStatus._member_names_)}"
            )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "status": "Created",
                "user_id": 1,
                "building_id": 1
            }
        }


class ShelvingJobBaseOutput(BaseModel):
    id: int
    status: Optional[str]
    origin: Optional[str]
    building_id: Optional[int] = None
    last_transition: Optional[datetime] = None
    run_time: Optional[timedelta] = None
    user: Optional[UserDetailReadOutput] = None
    create_dt: datetime
    update_dt: datetime


class ShelvingJobListOutput(ShelvingJobBaseOutput):
    non_tray_items: list = Field(exclude=True)
    trays: list = Field(exclude=True)

    @computed_field(title='Tray Count')
    @property
    def tray_count(self) -> int:
        return len(self.trays)

    @computed_field(title='NonTray Count')
    @property
    def non_tray_item_count(self) -> int:
        return len(self.non_tray_items)

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "Created",
                "origin": "Verification",
                "building_id": 1,
                "user": {
                    "id": 1,
                    "first_name": "Frodo",
                    "last_name": "Baggins",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "tray_count": 10,
                "non_tray_item_count": 5
            }
        }


class VerificationJobNestedForShelvingJob(BaseModel):
    id: int
    trayed: bool


class NestedShelfPositionNumberForShelvingJob(BaseModel):
    number: int


class NestedLadderNumberForShelvingJob(BaseModel):
    number: int


class NestedSideOrientationForShelvingJob(BaseModel):
    name: str


class NestedAisleNumberForShelvingJob(BaseModel):
    number: int


class NestedModuleForShelvingJob(BaseModel):
    id: int
    module_number: str


class NestedBuildingForShelvingJob(BaseModel):
    id: int
    name: str


class NestedAisleForShelvingJob(BaseModel):
    id: int
    aisle_number: NestedAisleNumberForShelvingJob
    module: Optional[NestedModuleForShelvingJob] = None
    building: Optional[NestedBuildingForShelvingJob] = None


class NestedSideForShelvingJob(BaseModel):
    id: int
    side_orientation: NestedSideOrientationForShelvingJob
    aisle: NestedAisleForShelvingJob


class NestedLadderForShelvingJob(BaseModel):
    id: int
    ladder_number: NestedLadderNumberForShelvingJob
    side: NestedSideForShelvingJob


class NestedShelfNumberForShelvingJob(BaseModel):
    number: int


class NestedShelfForShelvingJob(BaseModel):
    id: int
    barcode: BarcodeDetailReadOutput
    ladder: NestedLadderForShelvingJob
    shelf_number: NestedShelfNumberForShelvingJob


class ShelfPositionNestedForShelvingJob(BaseModel):
    id: int
    shelf_position_number: NestedShelfPositionNumberForShelvingJob
    shelf: NestedShelfForShelvingJob


class NestedOwnerForShelvingJob(BaseModel):
    id: int
    name: Optional[str] = None


class NestedSizeClassForShelvingJob(BaseModel):
    id: int
    name: str
    short_name: str


class TrayNestedForShelvingJob(BaseModel):
    id: int
    owner: Optional[NestedOwnerForShelvingJob] = None
    size_class: Optional[NestedSizeClassForShelvingJob] = None
    shelf_position_id: Optional[int] = None
    shelf_position: Optional[ShelfPositionNestedForShelvingJob] = None
    shelf_position_proposed_id: Optional[int] = None
    barcode: BarcodeDetailReadOutput
    container_type: Optional[ContainerTypeDetailReadOutput]
    scanned_for_shelving: Optional[bool] = None


class NonTrayNestedForShelvingJob(BaseModel):
    id: int
    owner: Optional[NestedOwnerForShelvingJob] = None
    size_class: Optional[NestedSizeClassForShelvingJob] = None
    shelf_position_id: Optional[int] = None
    shelf_position: Optional[ShelfPositionNestedForShelvingJob] = None
    shelf_position_proposed_id: Optional[int] = None
    barcode: BarcodeDetailReadOutput
    container_type: Optional[ContainerTypeDetailReadOutput]
    scanned_for_shelving: Optional[bool] = None


class NestedBuildingForShelvingJob(BaseModel):
    id: int
    name: Optional[str] = None


class ShelvingJobDetailOutput(ShelvingJobBaseOutput):
    user_id: Optional[int] = None
    verification_jobs: Optional[List[VerificationJobNestedForShelvingJob]] = []
    trays: List[TrayNestedForShelvingJob]
    non_tray_items: List[NonTrayNestedForShelvingJob]
    building: Optional[NestedBuildingForShelvingJob] = None

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
                "origin": "Verification",
                "building_id": 1,
                "building": {
                    "id": 1,
                    "name": "Fort Meade"
                },
                "user_id": 1,
                "user": {
                    "id": 1,
                    "first_name": "Frodo",
                    "last_name": "Baggins",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "verification_jobs": [
                    {
                        "id": 1,
                        "trayed": True
                    }
                ],
                "trays": [
                    {
                        "id": 1,
                        "owner": {
                            "id": 1,
                            "name": "Library Of Congress"
                        },
                        "size_class": {
                            "id": 1,
                            "name": "Record Storage",
                            "short_name": "RS"
                        },
                        "shelf_position_id": 1,
                        "shelf_position_proposed_id": 1,
                        "scanned_for_shelving": False,
                        "container_type": {
                            "id": 1,
                            "type": "Tray",
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "shelf_position": {
                            "id": 1,
                            "shelf_position_number": {
                                "number": 5
                            },
                            "shelf": {
                                "id": 1,
                                "shelf_number": {
                                    "number": 1,
                                },
                                "barcode": {
                                    "id": "44ffs-e29b-41d4-a716-446655440000",
                                    "value": "4401234123457",
                                    "type_id": 1,
                                    "create_dt": "2023-10-08T20:46:56.764426",
                                    "update_dt": "2023-10-08T20:46:56.764398"
                                },
                                "ladder": {
                                    "id": 1,
                                    "ladder_number": {
                                        "number": 1
                                    },
                                    "side": {
                                        "id": 27,
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
                                                "name": "Southpoint Circle"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                ],
                "non_tray_items": [
                    {
                        "id": 1,
                        "owner": {
                            "id": 1,
                            "name": "Library Of Congress"
                        },
                        "size_class": {
                            "id": 1,
                            "name": "Record Storage",
                            "short_name": "RS"
                        },
                        "shelf_position_id": 1,
                        "shelf_position_proposed_id": 1,
                        "scanned_for_shelving": False,
                        "container_type": {
                            "id": 2,
                            "type": "Non-Tray",
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "barcode": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "value": "5901234123457",
                            "type_id": 1,
                            "create_dt": "2023-10-08T20:46:56.764426",
                            "update_dt": "2023-10-08T20:46:56.764398"
                        },
                        "shelf_position": {
                            "id": 1,
                            "shelf_position_number": {
                                "number": 5
                            },
                            "shelf": {
                                "id": 1,
                                "shelf_number": {
                                    "number": 1,
                                },
                                "barcode": {
                                    "id": "44ffs-e29b-41d4-a716-446655440000",
                                    "value": "4401234123457",
                                    "type_id": 1,
                                    "create_dt": "2023-10-08T20:46:56.764426",
                                    "update_dt": "2023-10-08T20:46:56.764398"
                                },
                                "ladder": {
                                    "id": 1,
                                    "ladder_number": {
                                        "number": 1
                                    },
                                    "side": {
                                        "id": 27,
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
                                                "name": "Southpoint Circle"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class ReAssignmentInput(BaseModel):
    """
    Custom input with no underlying model.
    This is used for manually re-assigning containers during
    a ShelvingJob

    Path operation expects either shelf barcode value OR shelf_id
    """
    container_id: Optional[int] = None
    container_barcode_value: Optional[str] = None
    trayed: Optional[bool] = None
    shelf_position_number: int
    shelf_id: Optional[int] = None
    shelf_barcode_value: Optional[str] = None
    scanned_for_shelving: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "container_id": 1,
            "container_barcode_value": "yx233lnb",
            "trayed": True,
            "shelf_position_number": 5,
            "shelf_id": 1,
            "shelf_barcode_value": "xy332bnl",
            "scanned_for_shelving": True
        }


class ReAssignmentOutput(BaseModel):
    """
    Designed to be container agnostic,
    returns Tray or NonTrayItem data.
    """
    id: int
    shelving_job_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    shelf_position_proposed_id: Optional[int] = None
    scanned_for_shelving: Optional[bool] = None
    barcode: BarcodeDetailReadOutput
    owner: Optional[NestedOwnerForShelvingJob] = None
    size_class: Optional[NestedSizeClassForShelvingJob] = None
    shelf_position: Optional[ShelfPositionNestedForShelvingJob] = None
    container_type: Optional[ContainerTypeDetailReadOutput] = None

    class Config:
        json_schema_extra = {
            "id": 1,
            "shelving_job_id": 1,
            "shelf_position_id": 242,
            "shelf_position_proposed_id": 200,
            "scanned_for_shelving": True,
            "barcode": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "value": "5901234123457",
                "type_id": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            },
            "owner": {
                "id": 1,
                "name": "Library Of Congress"
            },
            "size_class": {
                "id": 1,
                "name": "Record Storage",
                "short_name": "RS"
            },
            "container_type": {
                "id": 2,
                "type": "Non-Tray",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            },
            "shelf_position": {
                "id": 1,
                "shelf_position_number": {
                    "number": 5
                },
                "shelf": {
                    "id": 1,
                    "barcode": {
                        "id": "44ffs-e29b-41d4-a716-446655440000",
                        "value": "4401234123457",
                        "type_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "ladder": {
                        "id": 1,
                        "ladder_number": {
                            "number": 1
                        },
                        "side": {
                            "id": 27,
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
                                    "name": "Southpoint Circle"
                                }
                            }
                        }
                    }
                }
            }
        }
