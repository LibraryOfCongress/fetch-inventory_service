"""Add Move types to shelving_mode enum

Revision ID: 70d0a34dcda3
Revises: 6e36473282a8
Create Date: 2026-01-24 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70d0a34dcda3'
down_revision: Union[str, None] = '6e36473282a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("COMMIT")
    op.execute("ALTER TYPE shelving_mode ADD VALUE 'MoveTrayItem'")
    op.execute("ALTER TYPE shelving_mode ADD VALUE 'MoveShelf'")
    op.execute("BEGIN")


def downgrade() -> None:
    # Postgres ENUMs are hard to downgrade without dropping/recreating.
    pass
