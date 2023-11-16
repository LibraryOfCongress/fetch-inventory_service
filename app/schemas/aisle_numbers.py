from pydantic import BaseModel, conint
from datetime import datetime


class AisleNumberInput(BaseModel):
    number: conint(ge=0, le=32767)

    class Config:
        json_schema_extra = {"example": {"number": 1}}


class AisleNumberBaseOutput(BaseModel):
    id: int
    number: int


class AisleNumberListOutput(AisleNumberBaseOutput):
    id: int
    number: int

    class Config:
        json_schema_extra = {"example": {"id": 1, "number": 1}}


class AisleNumberDetailOutput(AisleNumberBaseOutput):
    create_dt: datetime
    update_dt: datetime
    aisles: list

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "number": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "aisles": [
                    {
                        "aisle_number_id": 4,
                        "building_id": 1,
                        "create_dt": "2023-10-18T11:46:24.748946",
                        "id": 24,
                        "module_id": None,
                        "update_dt": "2023-10-18T11:46:24.748962",
                    },
                    {
                        "aisle_number_id": 4,
                        "building_id": None,
                        "create_dt": "2023-10-18T11:46:24.748946",
                        "id": 26,
                        "module_id": 1,
                        "update_dt": "2023-10-18T11:46:24.748962",
                    },
                ],
            }
        }
