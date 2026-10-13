"""Permission-model behaviour tests (v1.05 adoption + permissions-corrections doc).

These assert the *intended role behaviour* of the permission gates, complementing
the generic breadth checks in test_rbac.py. Each case drives a specific permission
set through a route and checks only whether the RequiresPermission gate let it
through — the handler's own outcome (200/404/422/…) is irrelevant here.

Covered:
  - Location hierarchy READS are open to any authenticated worker; WRITES still
    require can_manage_locations  (doc issues #12 shelf search & #13 hierarchy nav).
  - Barcode create/update/delete accept accession OR verification (doc #1, any_of).
  - Tray / item / non-tray edits accept accession OR verification OR the standalone
    can_edit_* permission (doc #2/#3).
  - Job dashboards (shelving / picklist / refile) are readable by a Viewer holding
    only the can_access_* permission (doc #5/#7/#8 — prefix gate removed).
  - Verification / accession job cancellation requires the can_cancel_* permission
    (doc #4/#14 — production naming, which the frontend bundles already use).
"""
import pytest

from app.auth.dependencies import get_current_user_with_permissions
from app.main import app as fastapi_app


def _user_with(perms):
    class P:
        def __init__(self, name):
            self.name = name

    class G:
        permissions = [P(p) for p in perms]

    class U:
        id = 1
        first_name = "Perm"
        last_name = "Tester"
        groups = [G()]

    return U()


def _override(perms):
    """Force the auth dependency to return a user with exactly ``perms``."""
    prev = fastapi_app.dependency_overrides.get(get_current_user_with_permissions)
    fastapi_app.dependency_overrides[get_current_user_with_permissions] = lambda: _user_with(perms)
    return prev


def _restore(prev):
    if prev is not None:
        fastapi_app.dependency_overrides[get_current_user_with_permissions] = prev
    else:
        fastapi_app.dependency_overrides.pop(get_current_user_with_permissions, None)


def _gate_rejected(resp):
    """True only when the permission gate itself blocked the request."""
    return resp.status_code == 401 or (
        resp.status_code == 403 and "Permission denied" in resp.text
    )


def _request(client, perms, method, url, **kw):
    prev = _override(perms)
    try:
        return client.request(method, url, **kw)
    finally:
        _restore(prev)


# A plain warehouse worker: authenticated, but no location-management rights.
WORKER = ["can_access_accession"]

# --------------------------------------------------------------------------- #
# Doc #12 / #13 — location hierarchy reads open, writes admin-only
# --------------------------------------------------------------------------- #
LOCATION_READS = [
    "/shelves/",
    "/shelves/1",
    "/shelves/barcode/TESTBARCODE",   # #12: shelf search during daily work
    "/shelves/positions/",
    "/shelves/positions/1",
    "/buildings/",
    "/buildings/1",
    "/modules/",
    "/modules/1",
    "/aisles/",
    "/ladders/",
    "/sides/",
]

LOCATION_WRITES = [
    ("POST", "/shelves/"),
    ("PATCH", "/shelves/1"),
    ("DELETE", "/shelves/1"),
    ("POST", "/buildings/"),
    ("PATCH", "/buildings/1"),
    ("DELETE", "/buildings/1"),
    ("POST", "/modules/"),
    ("POST", "/aisles/"),
    ("POST", "/ladders/"),
    ("POST", "/sides/"),
]


@pytest.mark.parametrize("url", LOCATION_READS)
def test_location_reads_open_to_workers(client, url):
    # A worker with no can_manage_locations must still be able to read location
    # data (navigate the hierarchy, search shelves) — doc #12/#13.
    resp = _request(client, WORKER, "GET", url)
    assert not _gate_rejected(resp), (
        f"GET {url} blocked a non-admin worker ({resp.status_code}): reads must stay open."
    )


@pytest.mark.parametrize("method,url", LOCATION_WRITES)
def test_location_writes_require_manage_locations(client, method, url):
    # Same worker must be rejected on writes...
    resp = _request(client, WORKER, method, url)
    assert resp.status_code == 403 and "Permission denied" in resp.text, (
        f"{method} {url} should require can_manage_locations; got {resp.status_code}."
    )


@pytest.mark.parametrize("method,url", LOCATION_WRITES)
def test_location_writes_pass_for_admin(client, method, url):
    # ...and allowed for a location manager (handler may 404/422, that's fine).
    resp = _request(client, ["can_manage_locations"], method, url)
    assert not _gate_rejected(resp), (
        f"{method} {url} blocked a can_manage_locations admin ({resp.status_code})."
    )


# --------------------------------------------------------------------------- #
# Doc #1 — barcode writes accept accession OR verification (any_of)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("method,url", [
    ("POST", "/barcodes/"),
    ("PATCH", "/barcodes/1"),
    ("DELETE", "/barcodes/1"),
])
@pytest.mark.parametrize("perms", [["can_access_accession"], ["can_access_verification"]])
def test_barcode_writes_accept_accession_or_verification(client, method, url, perms):
    resp = _request(client, perms, method, url)
    assert not _gate_rejected(resp), (
        f"{method} {url} blocked {perms[0]} — barcode writes must accept accession OR verification."
    )


@pytest.mark.parametrize("method,url", [
    ("POST", "/barcodes/"),
    ("PATCH", "/barcodes/1"),
    ("DELETE", "/barcodes/1"),
])
def test_barcode_writes_blocked_without_workflow_access(client, method, url):
    resp = _request(client, ["can_manage_locations"], method, url)
    assert resp.status_code == 403 and "Permission denied" in resp.text, (
        f"{method} {url} should reject a user lacking accession/verification access."
    )


# --------------------------------------------------------------------------- #
# Doc #2 / #3 — tray / item / non-tray edits: accession OR verification OR can_edit_*
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url,edit_perm", [
    ("/trays/1", "can_edit_tray"),
    ("/non_tray_items/1", "can_edit_non_tray_item"),
    ("/items/1", None),  # items have no standalone edit perm
])
@pytest.mark.parametrize("base", ["can_access_accession", "can_access_verification"])
def test_item_edits_accept_workflow_access(client, url, edit_perm, base):
    resp = _request(client, [base], "PATCH", url)
    assert not _gate_rejected(resp), (
        f"PATCH {url} blocked {base}; workflow staff must be able to edit."
    )


@pytest.mark.parametrize("url,edit_perm", [
    ("/trays/1", "can_edit_tray"),
    ("/non_tray_items/1", "can_edit_non_tray_item"),
])
def test_item_edits_accept_standalone_edit_permission(client, url, edit_perm):
    # The dedicated Item Management role (can_edit_*) still works.
    resp = _request(client, [edit_perm], "PATCH", url)
    assert not _gate_rejected(resp), (
        f"PATCH {url} blocked {edit_perm}; the standalone edit permission must still work."
    )


@pytest.mark.parametrize("url", ["/trays/1", "/non_tray_items/1", "/items/1"])
def test_item_edits_blocked_without_relevant_permission(client, url):
    resp = _request(client, ["can_manage_locations"], "PATCH", url)
    assert resp.status_code == 403 and "Permission denied" in resp.text, (
        f"PATCH {url} should reject a user without accession/verification/edit access."
    )


# --------------------------------------------------------------------------- #
# Doc #5 / #7 / #8 — job dashboards readable by Viewer (can_access_*), gate still present
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url,view_perm", [
    ("/shelving-jobs/", "can_access_shelving"),
    ("/pick-lists/", "can_access_picklist"),
    ("/refile-jobs/", "can_access_refile"),
])
def test_job_dashboard_readable_by_viewer(client, url, view_perm):
    resp = _request(client, [view_perm], "GET", url)
    assert not _gate_rejected(resp), (
        f"GET {url} blocked a Viewer holding {view_perm}; dashboards must be readable."
    )


@pytest.mark.parametrize("url", ["/shelving-jobs/", "/pick-lists/", "/refile-jobs/"])
def test_job_dashboard_still_gated(client, url):
    # Removing the prefix gate must not make the dashboard public to any authed user.
    resp = _request(client, ["can_manage_locations"], "GET", url)
    assert resp.status_code == 403 and "Permission denied" in resp.text, (
        f"GET {url} should still require the domain access permission."
    )


# --------------------------------------------------------------------------- #
# Doc #4 / #14 — cancellation requires the can_cancel_* permission (v1.05 naming)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url,access_perm,cancel_perm", [
    ("/verification-jobs/1", "can_access_verification", "can_cancel_verification_job"),
    ("/accession-jobs/1", "can_access_accession", "can_cancel_accession"),
])
def test_job_cancel_requires_cancel_permission(client, url, access_perm, cancel_perm):
    # With access + cancel -> passes the gate.
    ok = _request(client, [access_perm, cancel_perm], "DELETE", url)
    assert not _gate_rejected(ok), (
        f"DELETE {url} blocked a user holding {access_perm}+{cancel_perm}."
    )
    # With access but NOT cancel -> rejected.
    no = _request(client, [access_perm], "DELETE", url)
    assert no.status_code == 403 and "Permission denied" in no.text, (
        f"DELETE {url} must require {cancel_perm}, not just {access_perm}."
    )
