"""Self-service profile endpoint — PATCH /users/me.

Locks in the fix for the Settings -> Default Building 403: an authenticated,
non-admin user must be able to set their OWN default building without the
admin-only ``can_manage_groups_and_permissions`` that gates ``PATCH /users/{id}``.

Guarantees under test:
  - The restricted input schema only permits ``default_building_id`` — name /
    email / groups cannot be self-mutated even if sent in the body.
  - ``PATCH /users/me`` updates ONLY the requesting user's own record; a second
    user is left untouched.
  - Non-whitelisted fields in the body are ignored (not applied).
  - The admin ``PATCH /users/{id}`` endpoint still rejects the same non-admin
    user, so arbitrary-user edits were not loosened.
"""
from datetime import datetime, timezone

from sqlalchemy import text

from app.main import app as fastapi_app
from app.auth.dependencies import get_current_user_with_permissions
from app.models.users import User
from app.models.buildings import Building


def test_self_update_schema_whitelists_default_building_only():
    """Unknown fields must be dropped by the schema, not carried through."""
    from app.schemas.users import UserSelfUpdateInput

    data = UserSelfUpdateInput(
        **{"default_building_id": 7, "first_name": "x", "email": "y@z", "groups": [1]}
    ).model_dump(exclude_unset=True)
    assert data == {"default_building_id": 7}


def _override_user(user_id, session):
    """Force the auth dependency to return a specific real user for this request."""
    prev = fastapi_app.dependency_overrides.get(get_current_user_with_permissions)
    fastapi_app.dependency_overrides[get_current_user_with_permissions] = (
        lambda: session.get(User, user_id)
    )
    return prev


def _restore(prev):
    if prev is not None:
        fastapi_app.dependency_overrides[get_current_user_with_permissions] = prev
    else:
        fastapi_app.dependency_overrides.pop(get_current_user_with_permissions, None)


def _cleanup(session, emails, building_id):
    # Delete the referencing users and commit FIRST — default_building_id is a raw
    # FK column with no ORM relationship, so the unit of work won't order the
    # building delete after the users on its own.
    for email in emails:
        row = session.query(User).filter(User.email == email).first()
        if row is not None:
            session.delete(row)
    session.commit()
    if building_id is not None:
        b = session.get(Building, building_id)
        if b is not None:
            session.delete(b)
            session.commit()
    # Restore users_id_seq to its pre-test position. The test seed creates NO
    # users, so several domain tests rely on _get_or_create_user() minting the
    # FIRST user as id=1 (their mock auth hardcodes id=1). Creating+deleting our
    # own users here advances the sequence; without this reset the next user
    # minted becomes id>=3 and those tests break. setval(..., is_called=false)
    # makes the next nextval() return COALESCE(MAX(id),0)+1 (i.e. 1 when empty).
    session.execute(text(
        "SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 0) + 1, false)"
    ))
    session.commit()


def test_patch_users_me_updates_only_own_record(client, session):
    me_email = "selfsvc-me@test.local"
    other_email = "selfsvc-other@test.local"
    # Guard against leftovers from a prior interrupted run (unique email).
    _cleanup(session, [me_email, other_email], None)

    now = datetime.now(timezone.utc)
    building = Building(name="SelfSvc Bldg")
    session.add(building)
    session.commit()
    session.refresh(building)

    # A non-admin user (no groups -> no permissions) and an unrelated bystander.
    me = User(first_name="Me", last_name="Self", email=me_email,
              create_dt=now, update_dt=now)
    other = User(first_name="Other", last_name="Person", email=other_email,
                 create_dt=now, update_dt=now)
    session.add_all([me, other])
    session.commit()
    session.refresh(me)
    session.refresh(other)

    prev = _override_user(me.id, session)
    try:
        resp = client.patch(
            "/users/me",
            json={"default_building_id": building.id, "first_name": "SHOULD_IGNORE"},
        )
        assert resp.status_code == 200, resp.text

        session.expire_all()
        me_after = session.get(User, me.id)
        other_after = session.get(User, other.id)

        # Own building was set...
        assert me_after.default_building_id == building.id
        # ...the non-whitelisted field was ignored...
        assert me_after.first_name == "Me"
        # ...and the bystander is completely untouched.
        assert other_after.default_building_id is None

        # The admin endpoint must still reject this non-admin editing another user.
        forbidden = client.patch(f"/users/{other.id}", json={"first_name": "nope"})
        assert forbidden.status_code == 403 and "Permission denied" in forbidden.text
    finally:
        _restore(prev)
        _cleanup(session, [me_email, other_email], building.id)
