"""
CLI wrapper around seed_fake_data() that bootstraps the .env first.

Importing seed_fake_data triggers `from app.models.shelf_positions import
ShelfPosition` -> ... -> `app.config.config.get_settings()`, which fails
with `JWT_SECRET_KEY Field required` if pydantic-settings' default
relative-path .env lookup doesn't hit the file (deployed pods keep it at
/code/app/config/.env, not /code/.env).

Loading the .env explicitly into os.environ before the seed import lets
get_settings() find every required key, regardless of CWD.

Runnable as: python -m app.seed.run_seed_fake
"""

import os
import sys

from dotenv import load_dotenv

# Same candidate set as app.seed.wipe_db; first match wins.
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
    string-based relationships (e.g. Owner -> "Item") at mapper-config time.
    Branch-agnostic: community has app.models.all, develop does not."""
    import importlib
    import pkgutil

    import app.models
    for _, name, _ in pkgutil.walk_packages(
        app.models.__path__, app.models.__name__ + "."
    ):
        importlib.import_module(name)


if __name__ == "__main__":
    _load_env_or_die()
    # Imports deferred until AFTER env is loaded so get_settings() sees the keys.
    _import_all_models()

    # seed_fake_data references permissions by name (in group_permissions.json),
    # so the permissions table must be populated first. main.py's lifespan does
    # this at API startup, but the API process here was started against the
    # pre-wipe DB and won't re-seed automatically.
    from app.seed.seed_permissions_adhoc import seed_new_permissions
    print("Seeding permissions...")
    seed_new_permissions()

    from app.seed.seed_fake_data import seed_fake_data
    seed_fake_data()
