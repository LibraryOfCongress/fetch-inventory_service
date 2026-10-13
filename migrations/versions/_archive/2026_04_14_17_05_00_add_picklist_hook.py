"""add_picklist_hook

Revision ID: 2026_04_14_17_05_00
Revises: 2026_04_10_11_28_20
Create Date: 2026-04-14 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_04_14_17_05_00'
down_revision: Union[str, None] = '2026_04_10_11_28_20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to ils_configurations
    op.add_column('ils_configurations', sa.Column('expected_picklist_status', sa.String(length=100), nullable=False, server_default='In Transit'))
    op.add_column('ils_configurations', sa.Column('enable_picklist_hook', sa.Boolean(), nullable=False, server_default='false'))

    # 2. Add PICKLIST to workflow_action_enum
    # Postgres doesn't easily let you alter enums in a transaction block used by some alembic workflows, 
    # but op.execute with ALTER TYPE works outside a transaction or simply wrapped conditionally.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE workflow_action_enum ADD VALUE IF NOT EXISTS 'PICKLIST';")


def downgrade() -> None:
    op.drop_column('ils_configurations', 'enable_picklist_hook')
    op.drop_column('ils_configurations', 'expected_picklist_status')
    
    # We cannot easily remove a value from a Postgres ENUM type.
    # Therefore, we leave 'PICKLIST' in the enum during a downgrade. 
    pass
