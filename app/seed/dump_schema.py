"""
Runs `pg_dump --schema-only ...` against the DB this pod connects to,
streaming the dump to stdout. Robust to special characters in passwords
because it doesn't source .env in shell; it loads with python-dotenv,
parses the DSN with the same manual parser as wipe_db.py, and hands the
components to pg_dump via PG* env vars (also safe -- pg_dump reads them
without shell parsing).

Designed to be run as:

    kubectl -n fetch exec deploy/inventory-service -- \
        sh -c 'cd /code && python -m app.seed.dump_schema' > old_schema.sql

The stdout redirect on the operator side captures the dump file locally.
"""

import os
import subprocess
import sys

from app.seed.wipe_db import _load_env_or_die, _parse_dsn


PG_DUMP_FLAGS = [
    "--schema-only",
    "--no-owner",
    "--no-privileges",
    "--no-comments",
]


def main():
    _load_env_or_die()

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set after loading .env", file=sys.stderr)
        sys.exit(1)

    dsn = _parse_dsn(url)
    db_name = dsn.pop("_dbname") or "inventory_service"

    # Surface what we resolved to stderr so the dump file (stdout) stays clean.
    print(
        f"Dumping schema -> host={dsn['host']} port={dsn['port']} "
        f"user={dsn['user']} db={db_name}",
        file=sys.stderr,
    )

    pg_env = {
        **os.environ,
        "PGHOST": str(dsn["host"]),
        "PGPORT": str(dsn["port"]),
        "PGUSER": str(dsn["user"]),
        "PGPASSWORD": str(dsn["password"] or ""),
        "PGDATABASE": str(db_name),
    }

    result = subprocess.run(
        ["pg_dump", *PG_DUMP_FLAGS],
        env=pg_env,
        stdout=sys.stdout,  # straight-through to the operator's redirect
        stderr=sys.stderr,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
