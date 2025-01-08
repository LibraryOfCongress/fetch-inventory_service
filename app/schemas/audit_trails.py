from typing import Optional

from pydantic import BaseModel
from datetime import datetime


class AuditTrailBase(BaseModel):
    id: int
    table_name: str
    record_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "table_name": "accession_jobs",
                "record_id": "1"
            }
        }


class AuditTrailListOutput(AuditTrailBase):
    operation_type: str
    updated_by: Optional[str] = "System Generated"
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "table_name": "accession_jobs",
                "record_id": "1",
                "operation_type": "INSERT",
                "updated_by": "Frodo Baggins",
                "updated_at": "2023-10-08T20:46:56.764426"
            }
        }


class AuditTrailDetailOutput(AuditTrailBase):
    operation_type: str
    updated_by: str
    updated_at: datetime
    last_action: Optional[str] = None
    original_values: Optional[dict] = None
    new_values: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "table_name": "accession_jobs",
                "record_id": "1",
                "operation_type": "INSERT",
                "updated_by": "user1@loctest.gov",
                "updated_at": "2023-10-08T20:46:56.764426",
                "last_action": "Job status changed to Completed",
                "original_values": None,
                "new_values": {
                    "id": 1,
                    "name": "Organization",
                    "level": 1,
                    "create_dt": "2025-01-06T17:07:59.510626",
                    "update_dt": "2025-01-06T17:07:59.510643"
                }
            }
        }
