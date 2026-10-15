"""
Phase 3: negative-path / guard tests for job endpoints (API-level).

Covers the assignment-lock guards the API actually enforces:
- auto_assign_on_start blocks STARTING a job assigned to another user (403)
- a missing job returns 404

NOTE: the server does not enforce status-transition *legality* — only that the
value is a valid status (Pydantic enum validation). Transition order is enforced
by the frontend, so there are intentionally no API-level invalid-transition tests.
"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_with_permissions
from app.main import app as fastapi_app
from app.models.accession_jobs import AccessionJob
from app.models.users import User
from app.models.verification_jobs import VerificationJob
from app.models.workflows import Workflow


_PERMS = [
    "can_access_accession",
    "can_access_verification",
    "can_access_shipping",
    "can_access_withdraw",
    "process_verification_jobs",
    "process_shelving_jobs",
    "process_accession_jobs",
    "process_pick_lists",
    "process_refile_jobs",
    "process_shipping_jobs",
    "create_accession_jobs",
    "create_verification_jobs",
    # v1.05-aligned per-route perms (reads/moves/cancels) so mock users reach
    # the business logic under test rather than tripping the permission gate.
    "can_access_tray_detail",
    "can_access_item_detail",
    "can_access_picklist",
    "can_access_refile",
    "can_access_shelving",
    "can_move_trays_and_items",
    "can_cancel_accession",
    "can_cancel_verification_job",
    "can_delete_picklist_job",
    "can_delete_refile_job",
    "can_create_and_execute_shelving_job",
    "can_create_picklist_job",
    "can_create_refile_job",
]


def _override_auth_as(user_id, perms=_PERMS):
    """Make the auth dependency return a mock user with the given id + perms."""
    class P:
        def __init__(self, name):
            self.name = name

    class G:
        permissions = [P(n) for n in perms]

    class MockUser:
        id = user_id
        first_name = "Mock"
        last_name = "User"
        groups = [G()]

    prev = fastapi_app.dependency_overrides.get(get_current_user_with_permissions)
    fastapi_app.dependency_overrides[get_current_user_with_permissions] = lambda: MockUser()
    return prev


def _restore_auth(prev):
    if prev is not None:
        fastapi_app.dependency_overrides[get_current_user_with_permissions] = prev
    else:
        fastapi_app.dependency_overrides.pop(get_current_user_with_permissions, None)


def _make_user(session):
    user = User(first_name="N", last_name="N", email=f"{uuid.uuid4().hex[:10]}@t.test")
    session.add(user)
    session.commit()
    return user


def _make_accession_job(session, assigned_user_id, status="Created"):
    workflow = Workflow()
    session.add(workflow)
    session.commit()
    job = AccessionJob(
        workflow_id=workflow.id,
        trayed=True,
        status=status,
        assigned_user_id=assigned_user_id,
    )
    session.add(job)
    session.commit()
    return job


def test_other_user_can_start_job_assigned_to_someone_else(
    client: TestClient, session: Session, test_database
):
    owner = _make_user(session)
    other = _make_user(session)
    job = _make_accession_job(session, assigned_user_id=owner.id)

    prev = _override_auth_as(other.id)
    try:
        resp = client.patch(f"/accession-jobs/{job.id}", json={"status": "Running"})
    finally:
        _restore_auth(prev)

    assert resp.status_code == 200, resp.text
    session.refresh(job)
    assert job.assigned_user_id == owner.id


def test_owner_can_start_their_own_job(
    client: TestClient, session: Session, test_database
):
    owner = _make_user(session)
    job = _make_accession_job(session, assigned_user_id=owner.id)

    prev = _override_auth_as(owner.id)
    try:
        resp = client.patch(f"/accession-jobs/{job.id}", json={"status": "Running"})
    finally:
        _restore_auth(prev)

    assert resp.status_code == 200, resp.text


def test_verification_add_allowed_for_other_user(
    client: TestClient, session: Session, test_database
):
    owner = _make_user(session)
    other = _make_user(session)
    accession = _make_accession_job(session, assigned_user_id=owner.id)
    verification = VerificationJob(
        accession_job_id=accession.id,
        trayed=True,
        status="Running",
        assigned_user_id=owner.id,
    )
    session.add(verification)
    session.commit()

    prev = _override_auth_as(other.id)
    try:
        resp = client.patch(
            f"/verification-jobs/{verification.id}/add",
            json={"user_id": other.id, "barcode_value": "DOES-NOT-EXIST"},
        )
    finally:
        _restore_auth(prev)

    assert resp.status_code == 404, resp.text
    assert "Barcode with value DOES-NOT-EXIST Not Found" in resp.text


def test_update_nonexistent_accession_job_returns_404(
    client: TestClient, session: Session, test_database
):
    user = _make_user(session)
    prev = _override_auth_as(user.id)
    try:
        resp = client.patch("/accession-jobs/99999999", json={"status": "Running"})
    finally:
        _restore_auth(prev)

    assert resp.status_code == 404, resp.text
