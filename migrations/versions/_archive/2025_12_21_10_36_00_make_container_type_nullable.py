"""Make container_type_id nullable on shelves

Revision ID: 2025_12_21_10_36_00
Revises: 2025_04_11_17_22_40
Create Date: 2025-12-21 10:36:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2025_12_21_10_36_00'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make container_type_id nullable on shelves table
    op.alter_column('shelves', 'container_type_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    # Set any NULL values to default (1 = Tray) before making non-nullable
    op.execute("UPDATE shelves SET container_type_id = 1 WHERE container_type_id IS NULL")
    op.alter_column('shelves', 'container_type_id',
                    existing_type=sa.Integer(),
                    nullable=False)
