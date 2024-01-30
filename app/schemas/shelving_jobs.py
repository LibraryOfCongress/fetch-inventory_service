from pydantic import BaseModel, field_validator
from datetime import datetime, timedelta
from typing import Optional, List

from app.schemas.verification_jobs import VerificationJobDetailOutput


class ShelvingJobInput(BaseModel):
    status: Optional[str]
    user_id: Optional[int] = None
    last_transition: Optional[datetime]
    run_time: Optional[timedelta]
    verification_job_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "Created",
                "user_id": 1,
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "verification_job_id": 1
            }
        }


class ShelvingJobUpdateInput(BaseModel):
    status: Optional[str] = None
    user_id: Optional[int] = None
    last_transition: Optional[datetime] = None
    run_time: Optional[timedelta] = None
    verification_job_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "Created",
                "user_id": 1,
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "verification_job_id": 1
            }
        }


class ShelvingJobBaseOutput(BaseModel):
    id: int
    status: Optional[str]


class ShelvingJobListOutput(ShelvingJobBaseOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "status": "Created"
            }
        }


class ShelvingJobDetailOutput(ShelvingJobBaseOutput):
    user_id: Optional[int] = None
    last_transition: Optional[datetime]
    run_time: Optional[str]
    verification_jobs: List[Optional[VerificationJobDetailOutput]]
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
                "status": "Created",
                "user_id": 1,
                "last_transition": "2023-11-27T12:34:56.789123Z",
                "run_time": "03:25:15",
                "verification_jobs": [
                    {
                        "id": 1,
                        "trayed": True,
                        "status": "Created",
                        "user_id": 1,
                        "last_transition": "2023-11-27T12:34:56.789123Z",
                        "run_time": "03:25:15",
                        "accession_job_id": 1,
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
                        "create_dt": "2023-10-08T20:46:56.764426",
                        "update_dt": "2023-10-08T20:46:56.764398"
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398"
            }
        }
