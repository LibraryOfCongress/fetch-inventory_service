"""
Phase 5: CRUD / schema-contract tests for core lookup & location entities.

Drives the full create -> read -> list -> update -> delete lifecycle through the
API for each entity, catching serialization/validation regressions. Broad and
shallow by design; deep per-entity behavior lives in the workflow/domain tests.
"""
import random
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_with_permissions
from app.main import app as fastapi_app
from app.models.aisles import Aisle
from app.models.barcode_types import BarcodeType
from app.models.barcodes import Barcode
from app.models.buildings import Building
from app.models.ladders import Ladder
from app.models.modules import Module
from app.models.owner_tiers import OwnerTier
from app.models.side_orientations import SideOrientation
from app.models.sides import Side
from app.models.size_class import SizeClass

_PERMS = ["can_manage_locations", "can_manage_list_configurations"]


def _override_auth(perms=_PERMS):
    class P:
        def __init__(self, name):
            self.name = name

    class G:
        permissions = [P(p) for p in perms]

    class U:
        id = 1
        first_name = "Cfg"
        last_name = "Admin"
        groups = [G()]

    prev = fastapi_app.dependency_overrides.get(get_current_user_with_permissions)
    fastapi_app.dependency_overrides[get_current_user_with_permissions] = lambda: U()
    return prev


def _restore_auth(prev):
    if prev is not None:
        fastapi_app.dependency_overrides[get_current_user_with_permissions] = prev
    else:
        fastapi_app.dependency_overrides.pop(get_current_user_with_permissions, None)


def _u(prefix, length):
    return f"{prefix}{uuid.uuid4().hex[:8]}"[:length]


def _first_owner_tier_id(session):
    tier = session.query(OwnerTier).first()
    assert tier is not None, "seed data must provide an OwnerTier"
    return tier.id


def _first_size_class_id(session):
    sc = session.query(SizeClass).first()
    assert sc is not None, "seed data must provide a SizeClass"
    return sc.id


def _first_orientation_id(session):
    o = session.query(SideOrientation).first()
    assert o is not None, "seed data must provide a SideOrientation"
    return o.id


# Build just enough of the location hierarchy via ORM to satisfy a child's FK.
def _new_building(session):
    b = Building(name=_u("B", 25))
    session.add(b)
    session.commit()
    return b


def _new_module(session):
    m = Module(module_number=_u("M", 10), building_id=_new_building(session).id)
    session.add(m)
    session.commit()
    return m


def _new_aisle(session):
    a = Aisle(aisle_number=1, module_id=_new_module(session).id)
    session.add(a)
    session.commit()
    return a


def _new_side(session):
    s = Side(side_orientation_id=_first_orientation_id(session), aisle_id=_new_aisle(session).id)
    session.add(s)
    session.commit()
    return s


def _new_barcode(session):
    barcode_type = session.query(BarcodeType).first()
    bc = Barcode(value=uuid.uuid4().hex[:20], type_id=barcode_type.id, withdrawn=False)
    session.add(bc)
    session.commit()
    return bc


# Each spec: collection URL, detail template, create-payload factory(session),
# patch-payload factory(), and the field to verify after the patch.
SPECS = [
    dict(
        name="buildings", collection="/buildings/", detail="/buildings/{id}",
        make_create=lambda s: {"name": _u("B", 25)},
        make_patch=lambda: {"name": _u("Bp", 25)}, verify="name",
    ),
    dict(
        name="media_types", collection="/media-types/", detail="/media-types/{id}",
        make_create=lambda s: {"name": _u("MT", 25)},
        make_patch=lambda: {"name": _u("MTp", 25)}, verify="name",
    ),
    dict(
        name="container_types", collection="/container-types/", detail="/container-types/{id}",
        make_create=lambda s: {"type": _u("CT", 25)},
        make_patch=lambda: {"type": _u("CTp", 25)}, verify="type",
    ),
    dict(
        name="size_class", collection="/size_class/", detail="/size_class/{id}",
        make_create=lambda s: {
            "name": _u("SC", 50), "short_name": _u("s", 10),
            "height": "10.00", "width": "10.00", "depth": "10.00",
        },
        make_patch=lambda: {"name": _u("SCp", 50)}, verify="name",
    ),
    dict(
        name="barcode_types", collection="/barcodes/types", detail="/barcodes/types/{id}",
        make_create=lambda s: {"name": _u("BT", 40), "allowed_pattern": "^.{5}$"},
        # The barcode-types update schema requires `name`, so include it.
        make_patch=lambda: {"name": _u("BTp", 40), "allowed_pattern": "^.{6}$"},
        verify="allowed_pattern",
    ),
    dict(
        name="owners", collection="/owners/", detail="/owners/{id}",
        make_create=lambda s: {"name": _u("OW", 40), "owner_tier_id": _first_owner_tier_id(s)},
        make_patch=lambda: {"name": _u("OWp", 40)}, verify="name",
    ),
    # --- location hierarchy (FK chains built via ORM) ---
    dict(
        name="modules", collection="/modules/", detail="/modules/{id}",
        make_create=lambda s: {"building_id": _new_building(s).id, "module_number": _u("M", 50)},
        make_patch=lambda: {"module_number": _u("Mp", 50)}, verify="module_number",
    ),
    dict(
        name="aisles", collection="/aisles/", detail="/aisles/{id}",
        make_create=lambda s: {"aisle_number": 10, "module_id": _new_module(s).id},
        make_patch=lambda: {"aisle_number": 11}, verify="aisle_number",
    ),
    dict(
        name="sides", collection="/sides/", detail="/sides/{id}",
        make_create=lambda s: {"aisle_id": _new_aisle(s).id, "side_orientation_id": _first_orientation_id(s)},
        make_patch=None, verify=None,  # no clean scalar to mutate
    ),
    dict(
        name="ladders", collection="/ladders/", detail="/ladders/{id}",
        make_create=lambda s: {"side_id": _new_side(s).id, "ladder_number": 10},
        make_patch=lambda: {"ladder_number": 11}, verify="ladder_number",
    ),
    # --- remaining lookup / config tables ---
    dict(
        name="owner_tiers", collection="/owners/tiers", detail="/owners/tiers/{id}",
        make_create=lambda s: {"level": random.randint(1000, 32000), "name": _u("OT", 40)},
        make_patch=lambda: {"name": _u("OTp", 40)}, verify="name",
    ),
    dict(
        name="priorities", collection="/requests/priorities", detail="/requests/priorities/{id}",
        make_create=lambda s: {"value": _u("PR", 40)},
        make_patch=lambda: {"value": _u("PRp", 40)}, verify="value",
    ),
    dict(
        name="request_types", collection="/requests/types", detail="/requests/types/{id}",
        make_create=lambda s: {"type": _u("RT", 40)},
        make_patch=lambda: {"type": _u("RTp", 40)}, verify="type",
    ),
    dict(
        # barcode_id is required (matches the NOT NULL DB column and the model).
        name="conveyance_bins", collection="/conveyance-bins/", detail="/conveyance-bins/{id}",
        make_create=lambda s: {"barcode_id": str(_new_barcode(s).id)},
        make_patch=None, verify=None,  # only barcode_id is mutable
    ),
    dict(
        name="shelf_types", collection="/shelf-types/", detail="/shelf-types/{id}", create_status=200,
        make_create=lambda s: {"type": _u("ST", 50), "size_class_id": _first_size_class_id(s), "max_capacity": 5},
        make_patch=lambda: {"max_capacity": 7}, verify="max_capacity",
    ),
    dict(
        name="subcollection", collection="/subcollections/", detail="/subcollections/{id}",
        make_create=lambda s: {"name": _u("SUB", 40)},
        make_patch=lambda: {"name": _u("SUBp", 40)}, verify="name",
    ),
]


@pytest.mark.parametrize("spec", SPECS, ids=[s["name"] for s in SPECS])
def test_crud_lifecycle(spec, client: TestClient, session: Session, test_database):
    prev = _override_auth()
    try:
        # CREATE
        create_resp = client.post(spec["collection"], json=spec["make_create"](session))
        expected_create = spec.get("create_status", 201)
        assert create_resp.status_code == expected_create, f"create {spec['name']}: {create_resp.text}"
        created = create_resp.json()
        assert "id" in created, f"create {spec['name']} response missing id: {created}"
        resource_id = created["id"]
        detail_url = spec["detail"].format(id=resource_id)

        # READ (detail)
        get_resp = client.get(detail_url)
        assert get_resp.status_code == 200, f"get {spec['name']}: {get_resp.text}"
        assert get_resp.json()["id"] == resource_id

        # READ (list / Page schema)
        list_resp = client.get(spec["collection"])
        assert list_resp.status_code == 200, f"list {spec['name']}: {list_resp.text}"
        assert "items" in list_resp.json(), f"list {spec['name']} not paginated: {list_resp.json()}"

        # UPDATE (skipped for entities with no clean mutable scalar)
        if spec.get("make_patch"):
            patch_body = spec["make_patch"]()
            patch_resp = client.patch(detail_url, json=patch_body)
            assert patch_resp.status_code == 200, f"patch {spec['name']}: {patch_resp.text}"

            verified = client.get(detail_url).json()
            assert verified[spec["verify"]] == patch_body[spec["verify"]], (
                f"patch {spec['name']} did not persist {spec['verify']}: {verified}"
            )

        # DELETE
        del_resp = client.delete(detail_url)
        assert del_resp.status_code in (200, 204), f"delete {spec['name']}: {del_resp.text}"

        # After delete the resource must no longer be retrievable. Routers
        # previously wrapped GET handlers in a broad `except Exception` that
        # converted the intended NotFound into a 500; that's been fixed by
        # inserting `except HTTPException: raise` before the broad except, so
        # all routers should now return 404 here.
        post_delete = client.get(detail_url)
        assert post_delete.status_code == 404, (
            f"{spec['name']} expected 404 after delete, got "
            f"{post_delete.status_code}: {post_delete.text[:200]}"
        )
    finally:
        _restore_auth(prev)
