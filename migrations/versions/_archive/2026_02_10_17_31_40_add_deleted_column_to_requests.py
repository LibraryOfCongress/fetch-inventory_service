"""Add deleted column to requests

Revision ID: 2026_02_10_17_31_40
Revises: 2026_02_10_13_58_30
Create Date: 2026-02-10 17:31:40.468958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_10_17_31_40'
down_revision: Union[str, None] = '2026_02_10_13_58_30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('requests', sa.Column('deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('requests', 'deleted')
