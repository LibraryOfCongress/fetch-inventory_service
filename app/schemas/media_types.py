from typing import Optional
from pydantic import BaseModel, constr
from datetime import datetime

class MediaTypeInput(BaseModel):
    name: Optional[constr(max_length=25)] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Book"
            }
        }


class MediaTypeBaseReadOutput(BaseModel):
    id: int
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "Book"
            }
        }


class MediaTypeListOutput(MediaTypeBaseReadOutput):

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "Book"
            }
        }


class MediaTypeDetailWriteOutput(BaseModel):
    id: int
    name: str
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Book",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }


class MediaTypeDetailReadOutput(MediaTypeBaseReadOutput):
    create_dt: datetime
    update_dt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Book",
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
