"""Add indexes on date columns used to filter Raw Data Export queries

Revision ID: 2026_08_17_export_date_idx
Revises: 2026_06_24_batch_result
Create Date: 2026-08-17
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2026_08_17_export_date_idx'
down_revision: Union[str, None] = '2026_06_24_batch_result'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (index_name, table, column)
_LARGE_TABLE_INDEXES = [
    ("ix_items_accession_dt", "items", "accession_dt"),
    ("ix_non_tray_items_accession_dt", "non_tray_items", "accession_dt"),
]

_SMALL_TABLE_INDEXES = [
    ("ix_verification_jobs_create_dt", "verification_jobs", "create_dt"),
    ("ix_shelving_jobs_create_dt", "shelving_jobs", "create_dt"),
    ("ix_requests_create_dt", "requests", "create_dt"),
    ("ix_pick_lists_create_dt", "pick_lists", "create_dt"),
    ("ix_items_retrieval_events_create_dt", "items_retrieval_events", "create_dt"),
    ("ix_non_tray_items_retrieval_events_create_dt", "non_tray_items_retrieval_events", "create_dt"),
    ("ix_refile_jobs_create_dt", "refile_jobs", "create_dt"),
    ("ix_withdraw_jobs_create_dt", "withdraw_jobs", "create_dt"),
]


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for index_name, table, column in _LARGE_TABLE_INDEXES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} "
                f"ON {table} ({column})"
            )

    for index_name, table, column in _SMALL_TABLE_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for index_name, _table, _column in _LARGE_TABLE_INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}")

    for index_name, _table, _column in _SMALL_TABLE_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
