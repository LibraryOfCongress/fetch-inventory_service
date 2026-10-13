"""
CLI wrapper that creates (or refreshes) a System Administrators group with
ALL permissions attached, and adds a user to it. Use after wipe-and-seed,
or any time you need to ensure an SSO email has full admin access.

Mirrors the env-bootstrap + model-import pattern from run_seed_fake.py so
get_settings() can find JWT_SECRET_KEY and SQLAlchemy can resolve
cross-module string relationships before the first query.

Idempotent: re-runs are safe. Existing group, user, and group/user link
are all detected and reused.

Usage (inside the inventory-service pod):
    python -m app.seed.run_bootstrap_admin <email> [first_name] [last_name]

Example:
    python -m app.seed.run_bootstrap_admin admin@example.com System Admin
"""

import os
import sys

from dotenv import load_dotenv

# Same candidate set as app.seed.wipe_db / run_seed_fake; first match wins.
_ENV_FILE_CANDIDATES = [
    "/code/app/config/.env",
    "/app/config/.env",
    "/code/.env",
    ".env",
]


def _load_env_or_die():
    for path in _ENV_FILE_CANDIDATES:
        if os.path.exists(path):
            load_dotenv(path, override=False)
            print(f"Loaded env from: {path}")
            return
    print(
        "No .env found in any candidate location: "
        + ", ".join(_ENV_FILE_CANDIDATES),
        file=sys.stderr,
    )
    sys.exit(1)


def _import_all_models():
    """Walk app.models and import every submodule so SQLAlchemy can resolve
    string-based relationships at mapper-config time. Branch-agnostic."""
    import importlib
    import pkgutil

    import app.models
    for _, name, _ in pkgutil.walk_packages(
        app.models.__path__, app.models.__name__ + "."
    ):
        importlib.import_module(name)


def bootstrap_admin(email: str, first_name: str = "System", last_name: str = "Admin"):
    """Idempotently ensures a System Administrators group with all permissions
    exists, and that `email` is in it."""
    # Imports deferred until AFTER env + models are loaded.
    from app.seed.seeder_session import get_session
    from app.models.users import User
    from app.models.groups import Group
    from app.models.permissions import Permission

    session = get_session()

    admin_group = session.query(Group).filter_by(name="System Administrators").first()
    if not admin_group:
        print("Creating 'System Administrators' group")
        admin_group = Group(name="System Administrators")
        session.add(admin_group)

    # Always refresh permissions so a newly-added permission lands on existing
    # admin groups too.
    admin_group.permissions = session.query(Permission).all()

    user = session.query(User).filter_by(email=email).first()
    if not user:
        print(f"Creating user {email}")
        user = User(email=email, first_name=first_name, last_name=last_name)
        session.add(user)
    else:
        print(f"User {email} already exists; updating group membership")

    if admin_group not in user.groups:
        user.groups.append(admin_group)

    session.commit()
    print(
        f"Bootstrapped {user.email} into '{admin_group.name}' "
        f"with {len(admin_group.permissions)} permissions."
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python -m app.seed.run_bootstrap_admin <email> [first_name] [last_name]",
            file=sys.stderr,
        )
        sys.exit(1)

    email = sys.argv[1]
    first = sys.argv[2] if len(sys.argv) > 2 else "System"
    last = sys.argv[3] if len(sys.argv) > 3 else "Admin"

    _load_env_or_die()
    _import_all_models()
    bootstrap_admin(email, first, last)
