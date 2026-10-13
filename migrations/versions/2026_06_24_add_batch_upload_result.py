"""Add result column to batch_uploads (async bulk-upload outcome)

Stores the outcome of asynchronously-processed batch uploads so the frontend
can poll GET /batch-upload/{id} for the final status + result:
{"message": str, "shelves_created": int, "error_count": int, "errors": [...]}

Revision ID: 2026_06_24_batch_result
Revises: 2026_05_26_squash
Create Date: 2026-06-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_06_24_batch_result'
down_revision: Union[str, None] = '2026_05_26_squash'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # idempotent: skip if a prior partial run already added it
    op.execute(
        "ALTER TABLE batch_uploads ADD COLUMN IF NOT EXISTS result JSONB"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE batch_uploads DROP COLUMN IF EXISTS result")
