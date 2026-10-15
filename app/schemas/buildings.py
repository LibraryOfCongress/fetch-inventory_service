from typing import Optional, List
from pydantic import BaseModel, constr, ConfigDict
from datetime import datetime, timezone


class BuildingInput(BaseModel):
    name: constr(max_length=25, strict=False) = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Southpoint Circle"
            }
        }
    )


class BuildingUpdateInput(BaseModel):
    name: Optional[constr(max_length=25, strict=False)] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Southpoint Circle"
            }
        }
    )


class BuildingBaseOutput(BaseModel):
    id: int
    name: str | None
    create_dt: datetime
    update_dt: datetime


class BuildingListOutput(BuildingBaseOutput):

    model_config = ConfigDict(
        json_schema_extra={
            "example": [
                {
                    "id": 1,
                    "name": "Southpoint Circle",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                }
            ]
        }
    )


class BuildingDetailWriteOutput(BuildingBaseOutput):

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Southpoint Circle",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
    )


class AisleNumberNestedForBuilding(BaseModel):
    number: int


class AisleNestedForBuilding(BaseModel):
    id: int
    aisle_number: int


class ModuleNestedForBuilding(BaseModel):
    id: int
    module_number: str
    create_dt: datetime
    update_dt: datetime


class BuildingDetailReadOutput(BuildingBaseOutput):
    create_dt: datetime
    update_dt: datetime
    modules: List[ModuleNestedForBuilding]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Southpoint Circle",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "modules": [
                    {
                        "id": 1,
                        "module_number": "1",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                ]
            }
        }
    )
