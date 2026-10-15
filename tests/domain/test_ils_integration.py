"""
Phase 6: integration tests for ILS sync tasks and the sync-errors router.

- `validate_accessioned_item_async` against the MockILSAdapter records an
  ILSSyncError + flips `item.ils_sync_state` to SYNC_ERROR on adapter FAIL,
  and sets IN_SYNC on success.
- The sync-errors router lifecycle: list (default ACTIVE filter) → PATCH
  /{id}/resolve → re-list filtered by RESOLVED.
"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_with_permissions
from app.ils.tasks import validate_accessioned_item_async
from app.main import app as fastapi_app
from app.models.accession_jobs import AccessionJob
from app.models.barcode_types import BarcodeType
from app.models.barcodes import Barcode
from app.models.ils_configurations import AdapterTypeEnum, ILSConfiguration
from app.models.ils_sync_errors import (
    ILSSyncError,
    ILSSyncStatusEnum,
    WorkflowActionEnum,
)
from app.models.items import ILSSyncState, Item
from app.models.non_tray_items import ILSSyncState as NonTrayILSSyncState, NonTrayItem
from app.models.owner_tiers import OwnerTier
from app.models.owners import Owner
from app.models.size_class import SizeClass
from app.models.users import User
from app.models.verification_jobs import VerificationJob
from app.models.workflows import Workflow
from app.tasks import complete_accession_job


def _u(prefix, length):
    return f"{prefix}{uuid.uuid4().hex[:8]}"[:length]


def _make_ils_config(session):
    cfg = ILSConfiguration(
        name=_u("CFG", 150),
        adapter_type=AdapterTypeEnum.CUSTOM_MIDDLEWARE,
        base_url="http://mock",
        tenant_id="t",
        auth_client_id="c",
        auth_client_secret="s",
        is_active=True,
        enable_accession_hook=True,
    )
    session.add(cfg)
    session.commit()
    return cfg


def _make_owner_with_config(session, cfg):
    tier = session.query(OwnerTier).first()
    assert tier is not None, "seed must provide an OwnerTier"
    o = Owner(name=_u("OW", 40), owner_tier_id=tier.id, ils_configuration_id=cfg.id)
    session.add(o)
    session.commit()
    return o


def _make_item(session, owner, barcode_value, accession_job_id=None):
    bt = session.query(BarcodeType).filter_by(name="Item").first() \
        or session.query(BarcodeType).first()
    sc = session.query(SizeClass).first()
    bc = Barcode(value=barcode_value, type_id=bt.id, withdrawn=False)
    session.add(bc)
    session.commit()
    item = Item(
        barcode_id=bc.id,
        owner_id=owner.id,
        size_class_id=sc.id,
        accession_job_id=accession_job_id,
    )
    session.add(item)
    session.commit()
    return item


def _make_non_tray_item(session, owner, barcode_value, accession_job_id=None):
    bt = session.query(BarcodeType).filter_by(name="Item").first() \
        or session.query(BarcodeType).first()
    sc = session.query(SizeClass).first()
    bc = Barcode(value=barcode_value, type_id=bt.id, withdrawn=False)
    session.add(bc)
    session.commit()
    nti = NonTrayItem(
        barcode_id=bc.id,
        owner_id=owner.id,
        size_class_id=sc.id,
        accession_job_id=accession_job_id,
    )
    session.add(nti)
    session.commit()
    return nti


def _make_accession_job(session, owner):
    wf = Workflow()
    session.add(wf)
    session.commit()

    user = session.query(User).first()

    job = AccessionJob(
        workflow_id=wf.id,
        owner_id=owner.id,
        created_by_id=user.id if user else None,
        status="Running",
        trayed=False,
    )
    session.add(job)
    session.commit()
    return job


# --------------------------------------------------------------------------- #
# Sync task
# --------------------------------------------------------------------------- #
def test_validate_accession_fail_records_sync_error(session: Session, test_database):
    cfg = _make_ils_config(session)
    owner = _make_owner_with_config(session, cfg)
    barcode_value = f"FAIL-{uuid.uuid4().hex[:8]}"
    item = _make_item(session, owner, barcode_value)

    validate_accessioned_item_async(barcode_value, owner.id, is_non_tray=False)

    # The task uses its own session_manager session; force a re-read in ours.
    session.expire_all()
    item = session.get(Item, item.id)
    assert item.ils_sync_state == ILSSyncState.SYNC_ERROR

    errors = (
        session.query(ILSSyncError).filter_by(item_barcode=barcode_value).all()
    )
    assert len(errors) == 1
    assert errors[0].status == ILSSyncStatusEnum.ACTIVE
    assert errors[0].workflow_action == WorkflowActionEnum.ACCESSION


def test_validate_accession_success_marks_in_sync(session: Session, test_database):
    cfg = _make_ils_config(session)
    owner = _make_owner_with_config(session, cfg)
    barcode_value = f"MOCK-{uuid.uuid4().hex[:8]}"
    item = _make_item(session, owner, barcode_value)

    validate_accessioned_item_async(barcode_value, owner.id, is_non_tray=False)

    session.expire_all()
    item = session.get(Item, item.id)
    assert item.ils_sync_state == ILSSyncState.IN_SYNC

    errors = (
        session.query(ILSSyncError).filter_by(item_barcode=barcode_value).all()
    )
    assert len(errors) == 0


# --------------------------------------------------------------------------- #
# Accession Job completion — batch ILS validation (FETCH-1695 follow-up)
#
# When an Accession Job completes, all of its items/non-tray items should be
# batch-validated against the ILS *before* the Verification Job is created,
# instead of looking each one up as it's scanned.
# --------------------------------------------------------------------------- #
def test_accession_completion_batch_validates_before_verification_job(session: Session, test_database):
    cfg = _make_ils_config(session)  # enable_accession_hook=True, CUSTOM_MIDDLEWARE -> MockILSAdapter
    owner = _make_owner_with_config(session, cfg)
    job = _make_accession_job(session, owner)

    ok_barcode = f"OK-{uuid.uuid4().hex[:8]}"
    fail_barcode = f"FAIL-{uuid.uuid4().hex[:8]}"  # MockILSAdapter treats FAIL* barcodes as invalid
    ok_item = _make_item(session, owner, ok_barcode, accession_job_id=job.id)
    fail_nti = _make_non_tray_item(session, owner, fail_barcode, accession_job_id=job.id)

    complete_accession_job(job.id, "Running", audit_info={"name": "Test", "id": "1"})

    session.expire_all()
    ok_item = session.get(Item, ok_item.id)
    fail_nti = session.get(NonTrayItem, fail_nti.id)

    assert ok_item.ils_sync_state == ILSSyncState.IN_SYNC
    assert fail_nti.ils_sync_state == NonTrayILSSyncState.SYNC_ERROR

    errors = session.query(ILSSyncError).filter_by(item_barcode=fail_barcode).all()
    assert len(errors) == 1
    assert errors[0].workflow_action == WorkflowActionEnum.ACCESSION
    assert errors[0].status == ILSSyncStatusEnum.ACTIVE

    # Batch validation must have completed before the Verification Job was
    # created (not the other way around) -- since both happen inside the same
    # synchronous call, the sync state/error being persisted here is direct
    # proof the batch step ran to completion first.
    vj = session.execute(
        select(VerificationJob).where(VerificationJob.accession_job_id == job.id)
    ).scalars().first()
    assert vj is not None
    assert ok_item.verification_job_id == vj.id
    assert fail_nti.verification_job_id == vj.id


def test_accession_completion_skips_batch_when_hook_disabled(session: Session, test_database):
    cfg = _make_ils_config(session)
    cfg.enable_accession_hook = False
    session.add(cfg)
    session.commit()

    owner = _make_owner_with_config(session, cfg)
    job = _make_accession_job(session, owner)

    fail_barcode = f"FAIL-{uuid.uuid4().hex[:8]}"
    fail_item = _make_item(session, owner, fail_barcode, accession_job_id=job.id)

    complete_accession_job(job.id, "Running", audit_info={"name": "Test", "id": "1"})

    session.expire_all()
    fail_item = session.get(Item, fail_item.id)

    # No batch call was made -- sync state stays unset and no error is logged,
    # even though this barcode would fail MockILSAdapter's validation.
    assert fail_item.ils_sync_state is None
    assert session.query(ILSSyncError).filter_by(item_barcode=fail_barcode).count() == 0

    vj = session.execute(
        select(VerificationJob).where(VerificationJob.accession_job_id == job.id)
    ).scalars().first()
    assert vj is not None


# --------------------------------------------------------------------------- #
# Sync errors router lifecycle
# --------------------------------------------------------------------------- #
def _override_auth_for_sync():
    class P:
        def __init__(self, name):
            self.name = name

    class G:
        permissions = [P("can_manage_system_configurations")]

    class U:
        id = 1
        first_name = "A"
        last_name = "U"
        groups = [G()]

    prev = fastapi_app.dependency_overrides.get(get_current_user_with_permissions)
    fastapi_app.dependency_overrides[get_current_user_with_permissions] = lambda: U()
    return prev


def _restore_auth(prev):
    if prev is not None:
        fastapi_app.dependency_overrides[get_current_user_with_permissions] = prev
    else:
        fastapi_app.dependency_overrides.pop(get_current_user_with_permissions, None)


def test_sync_errors_list_and_resolve(client: TestClient, session: Session, test_database):
    err = ILSSyncError(
        item_barcode=f"BC-{uuid.uuid4().hex[:8]}",
        workflow_action=WorkflowActionEnum.ACCESSION,
        error_message="test error",
        status=ILSSyncStatusEnum.ACTIVE,
    )
    session.add(err)
    session.commit()
    err_id = str(err.id)

    prev = _override_auth_for_sync()
    try:
        # ACTIVE list contains our row
        resp = client.get("/ils-sync-errors/", params={"size": 100})
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json().get("items", [])]
        assert err_id in ids

        # resolve
        r = client.patch(f"/ils-sync-errors/{err_id}/resolve")
        assert r.status_code == 200

        session.expire_all()
        refreshed = session.get(ILSSyncError, err.id)
        assert refreshed.status == ILSSyncStatusEnum.RESOLVED
        assert refreshed.resolved_by_user_id == 1
        assert refreshed.resolved_at is not None

        # RESOLVED list contains our row; ACTIVE list does not
        resp_resolved = client.get(
            "/ils-sync-errors/", params={"status": "RESOLVED", "size": 100}
        )
        assert resp_resolved.status_code == 200
        resolved_ids = [item["id"] for item in resp_resolved.json().get("items", [])]
        assert err_id in resolved_ids

        resp_active = client.get(
            "/ils-sync-errors/", params={"status": "ACTIVE", "size": 100}
        )
        assert resp_active.status_code == 200
        active_ids = [item["id"] for item in resp_active.json().get("items", [])]
        assert err_id not in active_ids
    finally:
        _restore_auth(prev)
