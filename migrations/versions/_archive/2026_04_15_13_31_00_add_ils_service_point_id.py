"""add_ils_service_point_id

Revision ID: 2026_04_15_13_31_00
Revises: 2026_04_14_17_05_00
Create Date: 2026-04-15 13:31:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_04_15_13_31_00'
down_revision: Union[str, None] = '2026_04_14_17_05_00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ils_configurations', sa.Column('ils_service_point_id', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('ils_configurations', 'ils_service_point_id')
