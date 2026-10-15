# /code/app/schemas/aisles.py - REFACTORED: Removed AisleNumber dependency

import uuid

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional, List, Annotated

from app.schemas.modules import ModuleCustomDetailReadOutput


class AisleInput(BaseModel):
    aisle_number: Annotated[int, Field(ge=1, le=32767)]
    module_id: Optional[Annotated[int, Field(ge=0, le=32767)]] = None
    sort_priority: Optional[Annotated[int, Field(ge=0, le=32767)]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "aisle_number": 1,
                "module_id": 1,
                "sort_priority": 1
            }
        }
    )


class AisleUpdateInput(BaseModel):
    aisle_number: Optional[Annotated[int, Field(ge=1, le=32767)]] = None
    module_id: Optional[Annotated[int, Field(ge=0, le=32767)]] = None
    sort_priority: Optional[Annotated[int, Field(ge=0, le=32767)]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "aisle_number": 1,
                "module_id": 1,
                "sort_priority": 1
            }
        }
    )


class AisleBaseReadOutput(BaseModel):
    id: int
    aisle_number: int


class SideOrientationNestedForAisle(BaseModel):
    name: str


class SideNestedForAisle(BaseModel):
    id: int
    side_orientation: SideOrientationNestedForAisle


class AisleListOutput(AisleBaseReadOutput):
    sides: List[SideNestedForAisle]
    module: ModuleCustomDetailReadOutput | None
    sort_priority: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "aisle_number": 1,
                "module": {
                    "id": 1,
                    "module_number": "1",
                },
                "sides": [
                    {
                        "id": 1,
                        "side_orientation": {
                            "name": "Left"
                        }
                    }
                ]
            }
        }
    )


class AisleDetailWriteOutput(BaseModel):
    id: int
    aisle_number: int
    module_id: int | None = None
    sort_priority: Optional[int] = None
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "aisle_number": 1,
                "module_id": 1,
                "sort_priority": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
    )


class AisleDetailReadOutput(BaseModel):
    id: int
    aisle_number: int
    sort_priority: Optional[int] = None
    create_dt: datetime
    update_dt: datetime
    module: ModuleCustomDetailReadOutput | None
    sides: List[SideNestedForAisle]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "aisle_number": 1,
                "sort_priority": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "module": {
                    "id": 1,
                    "module_number": "1",
                },
                "sides": [
                    {
                        "id": 1,
                        "side_orientation": {
                            "name": "Left"
                        }
                    }
                ]
            }
        }
    )