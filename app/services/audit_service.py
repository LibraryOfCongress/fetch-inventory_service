# /code/app/services/audit_service.py
# Application-level audit logging service.

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_trails import AuditTrail

logger = logging.getLogger("app.services.audit_service")


# ---------------------------------------------------------------------------
# Event Type Constants
# ---------------------------------------------------------------------------

class AuditEventType:
    """Constants for audit event types."""

    # Job lifecycle
    JOB_CREATED = "job_created"
    JOB_STATUS_CHANGED = "status_changed"
    JOB_ASSIGNED = "job_assigned"
    JOB_COMPLETED = "job_completed"
    JOB_CANCELLED = "job_cancelled"
    JOB_DELETED = "job_deleted"

    # Item-level job actions
    ITEM_SCANNED = "item_scanned"
    ITEM_ADDED = "item_added"
    ITEM_REMOVED = "item_removed"
    ITEM_UPDATED = "item_updated"
    ITEM_PICKED = "item_picked"
    ITEM_REFILED = "item_refiled"
    ITEM_WITHDRAWN = "item_withdrawn"

    # Container/shelving actions
    CONTAINER_SHELVED = "container_shelved"
    CONTAINER_MOVED = "container_moved"
    CONTAINER_PREASSIGNED = "container_preassigned"

    # Request actions
    REQUEST_CREATED = "request_created"
    REQUEST_UPDATED = "request_updated"
    REQUEST_DELETED = "request_deleted"
    REQUEST_ADDED = "request_added"
    REQUEST_REMOVED = "request_removed"

    # Shipping actions
    BIN_SCANNED = "bin_scanned"
    BIN_CLEARED = "bin_cleared"

    # Entity CRUD actions
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_DELETED = "entity_deleted"
    ENTITY_MOVED = "entity_moved"
    ENTITY_INSERTED = "entity_inserted"


# Map event types to operation types for backward compatibility
_EVENT_TO_OPERATION = {
    AuditEventType.JOB_CREATED: "INSERT",
    AuditEventType.JOB_DELETED: "DELETE",
    AuditEventType.ENTITY_CREATED: "INSERT",
    AuditEventType.ENTITY_DELETED: "DELETE",
    AuditEventType.ENTITY_INSERTED: "INSERT",
    AuditEventType.REQUEST_CREATED: "INSERT",
    AuditEventType.REQUEST_DELETED: "DELETE",
}


# ---------------------------------------------------------------------------
# Core Logging Function
# ---------------------------------------------------------------------------

def log_audit_event(
    session: Session,
    event_type: str,
    description: str,
    *,
    job_type: Optional[str] = None,
    job_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    table_name: Optional[str] = None,
    record_id: Optional[str] = None,
    original_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
) -> None:
    """
    Log a structured audit event to the audit_log table.

    Reads user identity from ``session.audit_info`` (set by JWTMiddleware).
    Falls back to "System" / "0" when audit_info is unavailable (e.g. during
    background tasks that forgot to set it, or system-initiated operations).

    The event is added to the current session but **not** committed — callers
    should ensure a ``session.commit()`` happens as part of their normal flow.
    """
    # Read user info from session Python attribute (set by middleware)
    audit_info = getattr(session, "audit_info", None)

    if audit_info and audit_info.get("name") and audit_info["name"] != "System":
        user_name = audit_info["name"]
        user_id = str(audit_info.get("id", "0"))
    else:
        # Fallback: read from PostgreSQL session variables set by start_session_with_audit_info
        try:
            from sqlalchemy import text
            result = session.execute(text("SELECT current_setting('audit.user_name', true)")).scalar()
            user_id_result = session.execute(text("SELECT current_setting('audit.user_id', true)")).scalar()
            user_name = result if result else "System"
            user_id = user_id_result if user_id_result else "0"
        except Exception:
            user_name = "System"
            user_id = "0"

    # Derive operation_type from event_type
    operation_type = _EVENT_TO_OPERATION.get(event_type, "UPDATE")

    audit_entry = AuditTrail(
        event_type=event_type,
        description=description,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        job_type=job_type,
        job_id=str(job_id) if job_id is not None else None,
        table_name=table_name or job_type,
        record_id=record_id or (str(job_id) if job_id is not None else None),
        operation_type=operation_type,
        updated_at=datetime.now(timezone.utc),
        updated_by=user_name,
        updated_by_user_id=user_id,
        original_values=original_values,
        new_values=new_values,
    )

    session.add(audit_entry)
