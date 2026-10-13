"""
Phase 6: reporting contract smoke tests.

Auto-discovers the non-download, non-path-param GET endpoints under /reporting
and verifies that, against seeded data, each one returns 200 with a JSON body.
This catches handler crashes (500s), required-but-undocumented query params,
and serialization regressions across the broad reporting surface in one shot.

Detail-by-id endpoints (those with `{...}` in the path) are excluded since their
expected status depends on data; download/export endpoints are excluded because
they're streaming/long-running.
"""
import re

import pytest

from app.auth.dependencies import get_current_user_with_permissions
from app.main import app as fastapi_app
from app.models.buildings import Building


def _discover_reporting_endpoints():
    out = []
    for route in fastapi_app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set())
        if not path.startswith("/reporting"):
            continue
        if "GET" not in methods:
            continue
        if re.search(r"download|export", path):
            continue
        if "{" in path:  # detail-by-id needs data; skip from smoke
            continue
        out.append(path)
    return sorted(out)


REPORTING_ENDPOINTS = _discover_reporting_endpoints()


def _first_building_id(session):
    b = session.query(Building).first()
    assert b is not None, "seed should provide a Building"
    return b.id


# Endpoints with required query params get a factory; the rest use no params.
QUERY_PARAMS = {
    "/reporting/aisles/items_count/": lambda s: {"building_id": _first_building_id(s)},
    "/reporting/non_tray_items/count/": lambda s: {"building_id": _first_building_id(s)},
    "/reporting/tray_items/count/": lambda s: {"building_id": _first_building_id(s)},
}


def _override_auth():
    class P:
        def __init__(self, name):
            self.name = name

    class G:
        permissions = [P("can_access_reports")]

    class U:
        id = 1
        first_name = "Reports"
        last_name = "User"
        groups = [G()]

    prev = fastapi_app.dependency_overrides.get(get_current_user_with_permissions)
    fastapi_app.dependency_overrides[get_current_user_with_permissions] = lambda: U()
    return prev


def _restore_auth(prev):
    if prev is not None:
        fastapi_app.dependency_overrides[get_current_user_with_permissions] = prev
    else:
        fastapi_app.dependency_overrides.pop(get_current_user_with_permissions, None)


def test_reporting_endpoints_were_discovered():
    # Guardrail: if discovery breaks, parametrized tests would pass vacuously.
    assert len(REPORTING_ENDPOINTS) > 10


@pytest.mark.parametrize("path", REPORTING_ENDPOINTS, ids=REPORTING_ENDPOINTS)
def test_reporting_endpoint_smoke(client, session, test_database, path):
    params_factory = QUERY_PARAMS.get(path)
    params = params_factory(session) if params_factory else None
    prev = _override_auth()
    try:
        resp = client.get(path, params=params)
    finally:
        _restore_auth(prev)
    assert resp.status_code == 200, f"{path}: {resp.status_code} {resp.text[:300]}"
    # Body must be parseable JSON — catches serialization regressions.
    resp.json()
