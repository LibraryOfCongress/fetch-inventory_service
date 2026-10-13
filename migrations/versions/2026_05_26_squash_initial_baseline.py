"""Squash all migrations to 2026-05-26 baseline

This migration replaces the entire 158-revision chain that produced the
schema in production as of 2026-05-26. The previous migration files are
preserved at migrations/versions/_archive/ for historical reference but
are no longer in the active alembic path.

For databases that pre-date this squash (e.g., production at any old
revision), do NOT run this migration directly. Use the production-side
SQL transform script (see ops/migrate_to_squash.sql or equivalent) which
brings the existing schema up to this baseline and stamps alembic_version
to '2026_05_26_squash' in one transaction.

The upgrade body below is a verbatim execution of the canonical
pg_dump --schema-only output captured from a database that had run the
full migration chain end-to-end. Storing it as raw SQL (rather than
relying on alembic autogenerate) guarantees byte-equivalence between
this squash and the schema that prod-equivalent envs already run.

Revision ID: 2026_05_26_squash
Revises:
Create Date: 2026-05-26
"""

import os
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2026_05_26_squash'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_BASELINE_SQL_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "2026_05_26_squash_baseline.sql",
)


def upgrade() -> None:
    with open(_BASELINE_SQL_FILE, "r") as f:
        baseline_sql = f.read()
    # exec_driver_sql lets us run multi-statement SQL straight through
    # to psycopg2 without alembic trying to parameterize / split it.
    op.get_bind().exec_driver_sql(baseline_sql)


def downgrade() -> None:
    # This is the new baseline. Downgrading past it would mean reproducing
    # the original empty-database starting state, which means dropping
    # every table the baseline created. If you genuinely need that, do it
    # via `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` outside
    # alembic -- safer than enumerating drops here.
    raise NotImplementedError(
        "Cannot downgrade past the 2026-05-26 squash baseline. "
        "Use DROP SCHEMA public CASCADE manually if you need an empty DB."
    )
