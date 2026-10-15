"""add shipping fields to non tray items

Revision ID: 9c973da1bd66
Revises: 15a1422b2e56
Create Date: 2026-04-21 12:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c973da1bd66'
down_revision: Union[str, None] = '15a1422b2e56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to non_tray_items
    op.add_column('non_tray_items', sa.Column('shipping_bin_id', sa.BigInteger(), nullable=True))
    op.add_column('non_tray_items', sa.Column('scanned_for_shipping', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add foreign key constraint
    op.create_foreign_key('fk_non_tray_items_shipping_bin_id', 'non_tray_items', 'shipping_bins', ['shipping_bin_id'], ['id'])


def downgrade() -> None:
    # Remove foreign key and columns
    op.drop_constraint('fk_non_tray_items_shipping_bin_id', 'non_tray_items', type_='foreignkey')
    op.drop_column('non_tray_items', 'scanned_for_shipping')
    op.drop_column('non_tray_items', 'shipping_bin_id')
