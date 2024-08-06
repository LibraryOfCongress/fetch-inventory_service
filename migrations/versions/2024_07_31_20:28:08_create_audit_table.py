"""Create audit_table

Revision ID: 2024_07_31_20:28:08
Revises: 2024_07_27_15:55:29
Create Date: 2024-08-01 00:28:08.848427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2024_07_31_20:28:08'
down_revision: Union[str, None] = '2024_07_27_15:55:29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('table_name', sa.String(50), nullable=False),
        sa.Column('record_id', sa.String(50), nullable=False),
        sa.Column('operation_type', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_by', sa.String(50), nullable=False),
        sa.Column('original_values', sa.JSON(), nullable=False),
        sa.Column('new_values', sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('audit_log')
