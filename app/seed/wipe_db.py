"""
Drops and recreates the inventory_service database.

Designed to be invoked from inside an inventory-service pod via
`python -m app.seed.wipe_db`. Reads DATABASE_URL from the env (.env or
container env), connects to the `postgres` admin DB on the same host
with the same credentials, and DROPs + CREATEs the target DB.

DESTRUCTIVE. The caller (helper.sh:refresh-deployed-db) is responsible
for any confirmation prompt.
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv


# Deployed pods keep .env at app/config/.env (relative to /code) rather than
# at /code/.env, so pydantic-settings' default lookup misses it. Try the
# known locations and load the first one that exists. Order matters --
# earlier entries win for cross-environment portability.
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
            return path
    print(
        "No .env found in any candidate location: "
        + ", ".join(_ENV_FILE_CANDIDATES),
        file=sys.stderr,
    )
    sys.exit(1)


def _parse_dsn(url):
    """Manual DSN parser, password-tolerant.

    urllib.parse.urlparse splits the netloc at the FIRST ':' after the
    userinfo, which falls apart when passwords contain ':', '/', '@',
    URL-encoded bytes, etc. -- the password ends up sitting where the
    port should be.

    Format expected: scheme://username:password@host:port/dbname[?params]

    Strategy:
        1. Strip the scheme (everything up to and including '://').
        2. rsplit on '@' once to find the boundary between userinfo and
           hostpart. Using the *last* '@' lets the password contain '@'.
        3. Split userinfo on the FIRST ':' so passwords can contain ':'.
        4. Strip any '?...' query off the hostpart.
        5. Split hostpath on FIRST '/' to separate host:port from dbname.
        6. rsplit host:port on the LAST ':' for host vs port.

    Returns a dict suitable for psycopg2.connect(**kwargs).
    """
    if "://" not in url:
        raise ValueError(f"DATABASE_URL has no scheme://: {url!r}")
    _, rest = url.split("://", 1)

    if "@" not in rest:
        raise ValueError("DATABASE_URL has no '@' separating userinfo from host")
    userinfo, hostpart = rest.rsplit("@", 1)

    if ":" in userinfo:
        username, password = userinfo.split(":", 1)
    else:
        username, password = userinfo, None

    # Drop query string if present (?sslmode=..., etc.)
    if "?" in hostpart:
        hostpath, _query = hostpart.split("?", 1)
    else:
        hostpath = hostpart

    # Separate host:port from dbname
    if "/" in hostpath:
        host_port, dbname = hostpath.split("/", 1)
    else:
        host_port, dbname = hostpath, ""

    # Split host:port (LAST ':' so IPv6 etc. don't break it)
    if ":" in host_port:
        host, port_str = host_port.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Non-numeric port in DATABASE_URL: {port_str!r}")
    else:
        host, port = host_port, 5432

    return {
        "host": host,
        "port": port,
        "user": username,
        "password": password,
        "_dbname": dbname,
    }


def wipe_and_recreate():
    _load_env_or_die()

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL still not set after loading .env", file=sys.stderr)
        sys.exit(1)

    dsn = _parse_dsn(url)
    db_name = dsn.pop("_dbname") or os.environ.get("DATABASE_NAME") or "inventory_service"
    print(
        f"Parsed connection -> host={dsn['host']} port={dsn['port']} "
        f"user={dsn['user']} db={db_name} password=***"
    )

    # Connect to the 'postgres' admin DB on the same host/credentials.
    # DROP DATABASE cannot run while connected to the database being dropped.
    conn_kwargs = dict(dsn, dbname="postgres")

    print(f"Connecting to admin DB to drop/recreate '{db_name}'...")
    conn = psycopg2.connect(**conn_kwargs)
    conn.autocommit = True  # DDL outside a transaction
    try:
        cur = conn.cursor()
        # WITH (FORCE) kills any remaining sessions on the target DB (pg14+).
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
        cur.execute(f'CREATE DATABASE "{db_name}"')
        print(f"Recreated database: {db_name}")
    finally:
        conn.close()


if __name__ == "__main__":
    wipe_and_recreate()
