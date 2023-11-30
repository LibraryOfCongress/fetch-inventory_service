from pydantic import BaseModel
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
    create_dt: datetime
    update_dt: datetime

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
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
