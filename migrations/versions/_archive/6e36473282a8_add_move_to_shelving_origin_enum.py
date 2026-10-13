"""Add Move to shelving_origin enum

Revision ID: 6e36473282a8
Revises: 2026_01_24_15_04_33
Create Date: 2026-01-24 15:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e36473282a8'
down_revision: Union[str, None] = '2026_01_24_15_04_33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("COMMIT")
    op.execute("ALTER TYPE shelving_origin ADD VALUE 'Move'")
    op.execute("BEGIN")


def downgrade() -> None:
    # Postgres ENUMs are hard to downgrade without dropping/recreating.
    pass
