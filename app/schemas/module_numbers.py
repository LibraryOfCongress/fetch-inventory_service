from pydantic import BaseModel, conint
from datetime import datetime


class ModuleNumberInput(BaseModel):
    number: conint(ge=0, le=32767)

    class Config:
        json_schema_extra = {
            "example": {
                "number": 1
            }
        }


class ModuleNumberListOutput(BaseModel):
    id: int
    number: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "number": 1
            }
        }


class ModuleNumberDetailOutput(BaseModel):
    id: int
    number: int
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "number": 1,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
