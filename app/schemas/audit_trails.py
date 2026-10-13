# /code/app/schemas/audit_trails.py - Updated for app-level audit logging

from typing import Optional

from pydantic import BaseModel, ConfigDict
from datetime import datetime, timezone


class AuditTrailBase(BaseModel):
    id: int
    table_name: Optional[str] = None
    record_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "table_name": "accession_jobs",
                "record_id": "1"
            }
        }
    )


class AuditTrailListOutput(AuditTrailBase):
    operation_type: Optional[str] = None
    event_type: Optional[str] = None
    description: Optional[str] = None
    updated_by: Optional[str] = "System Generated"
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "table_name": "accession_jobs",
                "record_id": "1",
                "operation_type": "UPDATE",
                "event_type": "status_changed",
                "description": "Status changed from Created to Running",
                "updated_by": "Frodo Baggins",
                "updated_at": "2023-10-08T20:46:56.764426"
            }
        }
    )


class AuditTrailDetailOutput(AuditTrailBase):
    operation_type: Optional[str] = None
    event_type: Optional[str] = None
    description: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    job_type: Optional[str] = None
    job_id: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: datetime
    last_action: Optional[str] = None
    original_values: Optional[dict] = None
    new_values: Optional[dict] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "table_name": "accession_jobs",
                "record_id": "1",
                "operation_type": "UPDATE",
                "event_type": "status_changed",
                "description": "Status changed from Created to Running",
                "entity_type": "items",
                "entity_id": "42",
                "job_type": "accession_jobs",
                "job_id": "1",
                "updated_by": "user1@example.com",
                "updated_at": "2023-10-08T20:46:56.764426",
                "last_action": "Status changed from Created to Running",
                "original_values": None,
                "new_values": None
            }
        }
    )