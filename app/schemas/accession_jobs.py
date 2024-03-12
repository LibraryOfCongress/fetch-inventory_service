from pydantic import BaseModel, field_validator
from datetime import datetime, timedelta
from typing import Optional

from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput


class AccessionJobInput(BaseModel):
    trayed: bool
    status: Optional[str]
    user_id: Optional[int] = None
    run_time: Optional[timedelta]
    last_transition: Optional[datetime]
    owner_id: Optional[int] = None
    container_type_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "trayed": True,
                "status": "Paused",
                "user_id": 1,
                "run_time": "03:25:15",
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "owner_id": 1,
                "container_type_id": 1
            }
        }


class AccessionJobUpdateInput(BaseModel):
    trayed: Optional[bool] = None
    status: Optional[str] = None
    user_id: Optional[int] = None
    run_time: Optional[timedelta] = None
    last_transition: Optional[datetime] = None
    owner_id: Optional[int] = None
    container_type_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "trayed": True,
                "status": "Paused",
                "user_id": 1,
                "run_time": "03:25:15",
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "owner_id": 1,
                "container_type_id": 1
            }
        }


class AccessionJobBaseOutput(BaseModel):
    id: int
    trayed: bool
    status: Optional[str]


class AccessionJobListOutput(AccessionJobBaseOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "trayed": True,
                "status": "Created"
            }
        }


class AccessionJobDetailOutput(AccessionJobBaseOutput):
    user_id: Optional[int] = None
    run_time: Optional[timedelta]
    last_transition: Optional[datetime]
    owner_id: Optional[int] = None
    container_type_id: Optional[int] = None
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    owner: Optional[OwnerDetailReadOutput] = None
    verification_job: Optional[list] = None
    items: list
    trays: list
    non_tray_items: list
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

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "trayed": True,
                "status": "Paused",
                "user_id": 1,
                "run_time": "03:25:15",
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "owner_id": 1,
                "container_type_id": 1,
                "owner": {
                    "id": 1,
                    "name": "Special Collection Directorate",
                    "owner_tier_id": 2,
                    "owner_tier": {
                        "id": 1,
                        "level": 2,
                        "name": "division",
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    },
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "container_type": {
                    "id": 1,
                    "type": "Tray",
                    "create_dt": "2023-10-08T20:46:56.764426",
                    "update_dt": "2023-10-08T20:46:56.764398"
                },
                "verification_job": [
                    {
                        "id": 1,
                        "status": "Created",
                        "user_id": 1,
                        "last_transition": "2023-11-27T12:34:56.789123Z",
                        "run_time": "03:25:15",
                        "accession_job_id": 1,
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                ],
                "items": ["..."],
                "trays": ["..."],
                "non_tray_items": ["..."],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
