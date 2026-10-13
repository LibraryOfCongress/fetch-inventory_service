"""add verified status

Revision ID: bf01acb11b05
Revises: 6bd613af0dd9
Create Date: 2025-12-18 17:50:13.894542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf01acb11b05'
down_revision: Union[str, None] = '6bd613af0dd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # item_status
    op.execute("ALTER TYPE item_status ADD VALUE 'Verified'")
    # non_tray_item_status
    op.execute("ALTER TYPE non_tray_item_status ADD VALUE 'Verified'")


def downgrade() -> None:
    # Postgres ENUM types do not support removing values easily.
    pass
