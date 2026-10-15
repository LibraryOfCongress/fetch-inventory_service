# /code/app/schemas/aisle_numbers.py - REFACRORED TO PYDANTIC V2

from pydantic import BaseModel, conint, Field, ConfigDict # <-- ADDED Field
from datetime import datetime, timezone
from typing import List, Annotated # <-- ADDED Annotated


# CRITICAL V2 FIX: Replaced V1 'conint' with V2 Annotated[int, Field(...)]
class AisleNumberInput(BaseModel):
    # SmallInteger in SQL is 32767 max
    number: Annotated[int, Field(ge=0, le=32767)]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "number": 1
            }
        }
    )


class AisleNumberBaseOutput(BaseModel):
    id: int
    number: int


class AisleNumberListOutput(AisleNumberBaseOutput):
    id: int
    number: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "number": 1
            }
        }
    )


class AisleNumberDetailOutput(AisleNumberBaseOutput):
    create_dt: datetime
    update_dt: datetime
    aisles: list

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "number": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
                "aisles": [
                    {
                        "aisle_number_id": 4,
                        "create_dt": "2023-10-18T11:46:24.748946",
                        "id": 24,
                        "module_id": 1,
                        "update_dt": "2023-10-18T11:46:24.748962"
                    },
                    {
                        "aisle_number_id": 4,
                        "create_dt": "2023-10-18T11:46:24.748946",
                        "id": 26,
                        "module_id": 2,
                        "update_dt": "2023-10-18T11:46:24.748962"
                    },
                ]
            }
        }
    )