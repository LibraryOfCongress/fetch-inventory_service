from typing import Optional, List
from pydantic import BaseModel, constr
from datetime import datetime


class BuildingInput(BaseModel):
    name: constr(max_length=25, strict=False) = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Southpoint Circle"
            }
        }


class BuildingUpdateInput(BaseModel):
    name: Optional[constr(max_length=25, strict=False)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Southpoint Circle"
            }
        }


class BuildingBaseOutput(BaseModel):
    id: int
    name: str | None


class BuildingListOutput(BuildingBaseOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Southpoint Circle"
            }
        }


class BuildingDetailWriteOutput(BuildingBaseOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Southpoint Circle",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class ModuleNumberNestedForBuilding(BaseModel):
    number: int


class ModuleNestedForBuilding(BaseModel):
    id: int
    module_number: ModuleNumberNestedForBuilding


class BuildingDetailReadOutput(BuildingBaseOutput):
    create_dt: datetime
    update_dt: datetime
    modules: List[ModuleNestedForBuilding]

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Southpoint Circle",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "modules": [
                    {
                        "id": 1,
                        "module_number": {
                            "number": 1
                        }
                    }
                ],
            }
        }
