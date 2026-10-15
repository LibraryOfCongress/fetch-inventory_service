"""
Phase 4: RBAC breadth.

Auto-discovers every ``RequiresPermission``-gated route by introspecting the app,
then verifies the gate on each:
  - unauthenticated                          -> 401
  - authenticated but missing the permission -> 403
  - authenticated WITH the permission        -> not blocked (GET routes only)

The 401/403 checks are safe for every method (incl. POST/PATCH/DELETE) because
RequiresPermission resolves — and rejects — before the request body is validated
and before the handler runs, so no side effects occur. The "authorized" check is
restricted to GET routes so we never execute a mutating handler.
"""
import re

import pytest

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.main import app as fastapi_app


def _permission_codes(dependant):
    """Recursively collect every RequiresPermission code in a route's dependant tree."""
    codes = set()
    for dep in dependant.dependencies:
        call = getattr(dep, "call", None)
        if isinstance(call, RequiresPermission):
            codes |= call.permission_codes
        codes |= _permission_codes(dep)
    return codes


def _discover_gated_routes():
    routes = {}
    for route in fastapi_app.routes:
        dependant = getattr(route, "dependant", None)
        methods = getattr(route, "methods", None)
        if not dependant or not methods:
            continue
        codes = _permission_codes(dependant)
        if not codes:
            continue
        url = re.sub(r"\{[^}]+\}", "1", route.path)  # fill path params with a dummy value
        for method in methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            routes[(method, route.path)] = (url, frozenset(codes))
    return [
        (method, path, url, codes)
        for (method, path), (url, codes) in sorted(routes.items())
    ]


GATED_ROUTES = _discover_gated_routes()
_GET_ROUTES = [
    r for r in GATED_ROUTES
    if r[0] == "GET" and not re.search(r"download|export|profiler", r[1])
]
_ALL_IDS = [f"{m} {p}" for m, p, _u, _c in GATED_ROUTES]
_GET_IDS = [f"{m} {p}" for m, p, _u, _c in _GET_ROUTES]


def _set_user(user_or_none):
    """Override the auth dependency; None removes it (simulates unauthenticated)."""
    prev = fastapi_app.dependency_overrides.get(get_current_user_with_permissions)
    if user_or_none is None:
        fastapi_app.dependency_overrides.pop(get_current_user_with_permissions, None)
    else:
        fastapi_app.dependency_overrides[get_current_user_with_permissions] = lambda: user_or_none
    return prev


def _restore_user(prev):
    if prev is not None:
        fastapi_app.dependency_overrides[get_current_user_with_permissions] = prev
    else:
        fastapi_app.dependency_overrides.pop(get_current_user_with_permissions, None)


def _user_with(perms):
    class P:
        def __init__(self, name):
            self.name = name

    class G:
        permissions = [P(p) for p in perms]

    class U:
        id = 1
        first_name = "Auth"
        last_name = "User"
        groups = [G()]

    return U()


def test_gated_routes_were_discovered():
    # Guardrail: if discovery silently breaks, the parametrized tests would pass
    # vacuously. We expect a large number of permission-gated routes.
    assert len(GATED_ROUTES) > 100


@pytest.mark.parametrize("method,path,url,perms", GATED_ROUTES, ids=_ALL_IDS)
def test_unauthenticated_is_rejected(client, method, path, url, perms):
    prev = _set_user(None)
    try:
        resp = client.request(method, url)
    finally:
        _restore_user(prev)
    assert resp.status_code == 401, f"{method} {path}: expected 401, got {resp.status_code}"


@pytest.mark.parametrize("method,path,url,perms", GATED_ROUTES, ids=_ALL_IDS)
def test_missing_permission_is_forbidden(client, method, path, url, perms):
    prev = _set_user(_user_with([]))
    try:
        resp = client.request(method, url)
    finally:
        _restore_user(prev)
    assert resp.status_code == 403, (
        f"{method} {path}: expected 403, got {resp.status_code}: {resp.text[:200]}"
    )


@pytest.mark.parametrize("method,path,url,perms", _GET_ROUTES, ids=_GET_IDS)
def test_correct_permission_passes_gate(client, method, path, url, perms):
    prev = _set_user(_user_with(perms))
    try:
        resp = client.request(method, url)
    finally:
        _restore_user(prev)
    # Only the permission gate's own rejections count as a failure here. A handler
    # may legitimately return 403 for other reasons (e.g. a disabled feature flag),
    # which is not the gate blocking an authorized user.
    gate_rejected = resp.status_code == 401 or (
        resp.status_code == 403 and "Permission denied" in resp.text
    )
    assert not gate_rejected, (
        f"{method} {path}: gate blocked an authorized user ({resp.status_code}): {resp.text[:200]}"
    )
