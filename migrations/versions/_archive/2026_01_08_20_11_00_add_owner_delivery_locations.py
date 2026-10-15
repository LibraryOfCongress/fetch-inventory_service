"""add owner_delivery_locations table

Revision ID: 2026_01_08_20_11_00
Revises: 2025_12_28_19_12_00
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_01_08_20_11_00'
down_revision = '2025_12_28_19_12_00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'owner_delivery_locations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_id', sa.SmallInteger(), nullable=False),
        sa.Column('delivery_location_id', sa.Integer(), nullable=False),
        sa.Column('create_dt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('update_dt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['owners.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['delivery_location_id'], ['delivery_locations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'delivery_location_id', name='uq_owner_delivery_location')
    )
    
    # Create indexes for faster lookups
    op.create_index('ix_owner_delivery_locations_owner_id', 'owner_delivery_locations', ['owner_id'])
    op.create_index('ix_owner_delivery_locations_delivery_location_id', 'owner_delivery_locations', ['delivery_location_id'])


def downgrade() -> None:
    op.drop_index('ix_owner_delivery_locations_delivery_location_id', table_name='owner_delivery_locations')
    op.drop_index('ix_owner_delivery_locations_owner_id', table_name='owner_delivery_locations')
    op.drop_table('owner_delivery_locations')
