"""add accessioned status

Revision ID: 6bd613af0dd9
Revises: 2025_04_24_18_29_11
Create Date: 2025-12-18 16:49:47.088649

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bd613af0dd9'
down_revision: Union[str, None] = '2025_04_24_18_29_11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # item_status
    op.execute("ALTER TYPE item_status ADD VALUE 'Accessioned'")
    # non_tray_item_status
    op.execute("ALTER TYPE non_tray_item_status ADD VALUE 'Accessioned'")


def downgrade() -> None:
    # Postgres ENUM types do not support removing values easily. 
    # This is generally irreversible without recreating the type.
    pass
