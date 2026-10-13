"""
Phase 7: integration tests for app/services/audit_service.py.

Verifies that ``log_audit_event`` writes an AuditTrail row with the right
fields, derives operation_type from the event-type map, and reads the user
identity from ``session.audit_info`` when set (falling back to "System").
"""
import uuid

from sqlalchemy.orm import Session

from app.models.audit_trails import AuditTrail
from app.services.audit_service import AuditEventType, log_audit_event


def _clear_audit_info(session):
    if hasattr(session, "audit_info"):
        try:
            del session.audit_info
        except AttributeError:
            pass


def test_log_audit_event_writes_row_with_defaults(session: Session, test_database):
    _clear_audit_info(session)
    desc = f"phase7-audit-{uuid.uuid4().hex[:8]}"
    log_audit_event(
        session,
        event_type=AuditEventType.JOB_STATUS_CHANGED,
        description=desc,
        job_type="accession_jobs",
        job_id=42,
    )
    session.commit()

    rows = session.query(AuditTrail).filter_by(description=desc).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.event_type == AuditEventType.JOB_STATUS_CHANGED
    assert row.job_type == "accession_jobs"
    assert row.job_id == "42"  # stringified per impl
    # Status-changed isn't in the operation-type map → defaults to UPDATE.
    assert row.operation_type == "UPDATE"
    # No audit_info on session → falls back to "System" / "0".
    assert row.updated_by == "System"
    assert row.updated_by_user_id == "0"


def test_log_audit_event_reads_audit_info_and_derives_insert(session: Session, test_database):
    _clear_audit_info(session)
    session.audit_info = {"name": "TestUser", "id": "99"}
    try:
        desc = f"phase7-audit-info-{uuid.uuid4().hex[:8]}"
        log_audit_event(
            session,
            event_type=AuditEventType.ENTITY_CREATED,
            description=desc,
            entity_type="building",
            entity_id=7,
        )
        session.commit()

        row = session.query(AuditTrail).filter_by(description=desc).first()
        assert row is not None
        assert row.updated_by == "TestUser"
        assert row.updated_by_user_id == "99"
        # ENTITY_CREATED maps to INSERT.
        assert row.operation_type == "INSERT"
        assert row.entity_type == "building"
        assert row.entity_id == "7"
    finally:
        _clear_audit_info(session)
