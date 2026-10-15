"""Add ShippingJob, ShippingBin, Item.Retrieved, Item.shipping_bin_id

Revision ID: 2026_02_17_15_01_14
Revises: 2026_02_10_17_31_40
Create Date: 2026-02-17 10:01:14.799530

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_02_17_15_01_14'
down_revision: Union[str, None] = '2026_02_10_17_31_40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add 'Retrieved' to item_status Enum
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT 1 FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid WHERE pg_type.typname = 'item_status' AND pg_enum.enumlabel = 'Retrieved'")).scalar()
    if not res:
        # Commit the current Alembic transaction to unlock the DB for the ALTER TYPE
        op.execute("COMMIT")
        op.execute("ALTER TYPE item_status ADD VALUE 'Retrieved'")
        op.execute("BEGIN")

    # 2. Create Shipping Jobs
    op.create_table('shipping_jobs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.Enum('Created', 'Assigned', 'Paused', 'Running', 'Completed', name='shipping_status'), nullable=False),
        sa.Column('completed_dt', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('run_time', sa.Interval(), nullable=True),
        sa.Column('last_transition', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('assigned_user_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('create_dt', sa.DateTime(timezone=True), nullable=False),
        sa.Column('update_dt', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create Shipping Bins
    op.create_table('shipping_bins',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('shipping_job_id', sa.BigInteger(), nullable=False),
        sa.Column('barcode', sa.String(length=255), nullable=False),
        sa.Column('delivery_location_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('Open', 'Closed', name='shipping_bin_status'), nullable=False),
        sa.Column('cleared_dt', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('cleared_by_id', sa.Integer(), nullable=True),
        sa.Column('create_dt', sa.DateTime(timezone=True), nullable=False),
        sa.Column('update_dt', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['cleared_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['delivery_location_id'], ['delivery_locations.id'], ),
        sa.ForeignKeyConstraint(['shipping_job_id'], ['shipping_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_shipping_bin_barcode_uncleared', 'shipping_bins', ['barcode', 'cleared_dt'], unique=False)
    op.create_index(op.f('ix_shipping_bins_barcode'), 'shipping_bins', ['barcode'], unique=False)
    op.create_index(op.f('ix_shipping_bins_shipping_job_id'), 'shipping_bins', ['shipping_job_id'], unique=False)

    # 4. Add Columns to Items
    op.add_column('items', sa.Column('shipping_bin_id', sa.BigInteger(), nullable=True))
    op.add_column('items', sa.Column('scanned_for_shipping', sa.Boolean(), server_default='false', nullable=False))
    
    # 5. Add Foreign Key
    op.create_foreign_key('fk_items_shipping_bin', 'items', 'shipping_bins', ['shipping_bin_id'], ['id'])


def downgrade() -> None:
    # Reverse operations
    op.drop_constraint('fk_items_shipping_bin', 'items', type_='foreignkey')
    op.drop_column('items', 'scanned_for_shipping')
    op.drop_column('items', 'shipping_bin_id')
    
    op.drop_index(op.f('ix_shipping_bins_shipping_job_id'), table_name='shipping_bins')
    op.drop_index(op.f('ix_shipping_bins_barcode'), table_name='shipping_bins')
    op.drop_index('idx_shipping_bin_barcode_uncleared', table_name='shipping_bins')
    op.drop_table('shipping_bins')
    
    op.drop_table('shipping_jobs')
    
    # We generally don't remove Enum values in downgrade as it's not supported by Postgres easily
    # op.execute("ALTER TYPE item_status DROP VALUE 'Retrieved'") # Not valid SQL
    # We also have to explicitly drop the types we created
    op.execute("DROP TYPE shipping_status")
    op.execute("DROP TYPE shipping_bin_status")
