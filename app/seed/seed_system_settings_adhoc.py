"""
Ad-hoc seeder for system_settings.

Loads rows from app/seed/fixtures/types/system_settings.json. Idempotent --
existing rows (matched by `key`) are left alone; missing keys are inserted.

Runnable from inside the inventory-service pod, e.g.:

    kubectl -n fetch exec -it deploy/inventory-service -- \
        sh -c 'cd /code && python -m app.seed.seed_system_settings_adhoc'

Or interactively from a python REPL in the container:

    >>> from app.seed.seed_system_settings_adhoc import seed_new_system_settings
    >>> seed_new_system_settings()
"""

import json
import os
import sys

from app.seed.seeder_session import get_session
from app.models.system_settings import SystemSetting


def seed_new_system_settings():
    print("Starting ad-hoc system_settings seeder...")
    session = get_session()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "fixtures", "types", "system_settings.json")
    if not os.path.exists(file_path):
        print(f"Fixture not found: {file_path}")
        return

    with open(file_path, "r") as f:
        json_content = json.load(f)
        settings_data = json_content["data"]

    try:
        existing = session.query(SystemSetting).all()
        existing_keys = {s.key for s in existing}
    except Exception as e:
        print(f"Error querying existing system_settings: {e}")
        return

    new_count = 0
    for s_data in settings_data:
        key = s_data["key"]
        if key in existing_keys:
            print(f"  exists, skipping: {key}")
            continue
        print(f"  adding: {key} = {s_data['value']!r}")
        session.add(SystemSetting(
            key=key,
            value=s_data["value"],
            description=s_data.get("description"),
        ))
        new_count += 1

    if new_count == 0:
        print("No new system_settings to add.")
        return

    try:
        session.commit()
        print(f"Committed {new_count} new system_settings.")
    except Exception as e:
        session.rollback()
        print(f"Error committing system_settings: {e}")
        sys.exit(1)


if __name__ == "__main__":
    seed_new_system_settings()
