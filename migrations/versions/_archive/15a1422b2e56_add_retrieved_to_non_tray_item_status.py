"""add retrieved to non tray item status

Revision ID: 15a1422b2e56
Revises: 2026_04_15_13_31_00
Create Date: 2026-04-21 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15a1422b2e56'
down_revision: Union[str, None] = '2026_04_15_13_31_00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres ENUM addition for non_tray_item_status
    # Using commit_as_inactive or manual execution because ALTER TYPE ADD VALUE cannot run in a transaction block
    op.execute("COMMIT")
    op.execute("ALTER TYPE non_tray_item_status ADD VALUE 'Retrieved'")


def downgrade() -> None:
    # Postgres ENUM types do not support removing values easily.
    pass
