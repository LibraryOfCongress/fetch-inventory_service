"""Regression guard: admin "manage" permissions gate writes, never reads.

Base users must be able to READ reference/config data (locations, owners,
dropdowns, users) to do their work (accessioning, shelving, requests). A prior
change applied admin "manage" permissions at the ROUTER level, which gated every
route — including GETs — and locked base users out. GETs are now
authenticated-only; writes keep the manage permission.

This introspects the live app (the runtime source of truth) and asserts, for the
impacted resource paths:
  - no GET is gated by the resource's admin "manage" permission, and
  - every write (POST/PUT/PATCH/DELETE) IS gated by it.

GETs may still be gated by *base* permissions in the future (that's fine); this
only forbids the admin manage permission on reads.
"""
import pytest

from app.auth.dependencies import RequiresPermission
from app.main import app as fastapi_app

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# resource path prefix -> the admin "manage" permission that must gate ONLY writes.
# Longest-prefix wins, so /shelves also covers /shelves/positions, /owners covers
# /owners/tiers, etc. The /requests/* and /barcodes/types entries are scoped
# narrowly so we don't touch the sibling request/barcode routers.
RESOURCE_PERM = {
    "/shelves": "can_manage_locations",            # incl. /shelves/positions
    "/buildings": "can_manage_locations",
    "/modules": "can_manage_locations",
    "/aisles": "can_manage_locations",
    "/ladders": "can_manage_locations",
    "/sides": "can_manage_locations",
    "/system-settings": "can_manage_system_configurations",
    "/owners": "can_manage_list_configurations",   # incl. /owners/tiers
    "/size_class": "can_manage_list_configurations",
    "/media-types": "can_manage_list_configurations",
    "/requests/priorities": "can_manage_list_configurations",
    "/requests/types": "can_manage_list_configurations",
    "/requests/locations": "can_manage_list_configurations",
    "/barcodes/types": "can_manage_list_configurations",    # barcode_types router only; main /barcodes
                                                            # create/update/delete now use accession/
                                                            # verification (see v1.05 model), not a manage perm
    "/subcollections": "can_manage_list_configurations",
    "/sides/orientations": "can_manage_list_configurations",  # side_orientations router (longest-prefix beats /sides)
    "/shelf-types": "can_manage_list_configurations",
    "/conveyance-bins": "can_manage_list_configurations",
    "/users": "can_manage_groups_and_permissions",
}

# (Previously /sides/orientations was excluded as an outlier; it is now folded in
# above with its own can_manage_list_configurations entry, which longest-prefix
# matching resolves ahead of the /sides -> can_manage_locations entry.)
#
# /users/me is a deliberate exception: an authenticated user updates only their
# OWN profile (default building) with no admin permission — the whole point of
# the self-service endpoint. It is intentionally NOT manage-gated, so exclude it
# from the "writes require the manage permission" assertion. (Own-record safety
# is covered by tests/auth/test_self_service_profile.py.)
EXCLUDE_PREFIXES = ("/users/me",)


def _permission_codes(dependant):
    codes = set()
    for dep in dependant.dependencies:
        call = getattr(dep, "call", None)
        if isinstance(call, RequiresPermission):
            codes |= call.permission_codes
        codes |= _permission_codes(dep)
    return codes


def _match_resource(path):
    if any(path == p or path.startswith(p + "/") or path.startswith(p) for p in EXCLUDE_PREFIXES):
        return None
    best = None
    for prefix in RESOURCE_PERM:
        if path == prefix or path.startswith(prefix + "/"):
            if best is None or len(prefix) > len(best):
                best = prefix
    return best


def _impacted_routes():
    out = []
    for route in fastapi_app.routes:
        dependant = getattr(route, "dependant", None)
        methods = getattr(route, "methods", None)
        if not dependant or not methods:
            continue
        resource = _match_resource(route.path)
        if resource is None:
            continue
        codes = _permission_codes(dependant)
        for method in methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            out.append((method, route.path, RESOURCE_PERM[resource], frozenset(codes)))
    return out


IMPACTED = _impacted_routes()
GETS = [r for r in IMPACTED if r[0] == "GET"]
WRITES = [r for r in IMPACTED if r[0] in WRITE_METHODS]
_GET_IDS = [f"{m} {p}" for m, p, _, _ in GETS]
_WRITE_IDS = [f"{m} {p}" for m, p, _, _ in WRITES]


def test_discovery_sane():
    # If introspection silently breaks, the parametrized tests would pass
    # vacuously. These floors are well below the real counts.
    assert len(GETS) >= 17, f"only discovered {len(GETS)} impacted GET routes"
    assert len(WRITES) >= 40, f"only discovered {len(WRITES)} impacted write routes"


@pytest.mark.parametrize("method,path,perm,codes", GETS, ids=_GET_IDS)
def test_get_not_blocked_by_manage_permission(method, path, perm, codes):
    assert perm not in codes, (
        f"{method} {path} is gated by admin '{perm}'; reads must stay open to base users."
    )


@pytest.mark.parametrize("method,path,perm,codes", WRITES, ids=_WRITE_IDS)
def test_write_requires_manage_permission(method, path, perm, codes):
    assert perm in codes, (
        f"{method} {path} is NOT gated by '{perm}'; writes must require the manage permission."
    )
