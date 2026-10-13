"""Add shelve_by_list feature tables and columns

Revision ID: 2026_01_16_18_10_00
Revises: 2026_01_08_20_11_00
Create Date: 2026-01-16 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_01_16_18_10_00'
down_revision = '2026_01_08_20_11_00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add 'List' value to shelving_origin enum
    op.execute("ALTER TYPE shelving_origin ADD VALUE IF NOT EXISTS 'List'")
    
    # 2. Create shelving_mode enum type
    op.execute("""
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'shelving_mode') THEN
                CREATE TYPE shelving_mode AS ENUM ('Manual', 'PreAssigned');
            END IF;
        END $$;
    """)
    
    # 3. Add new columns to shelving_jobs table
    op.add_column('shelving_jobs', sa.Column('mode', sa.Enum('Manual', 'PreAssigned', name='shelving_mode'), nullable=True))
    op.add_column('shelving_jobs', sa.Column('allow_unassigned_size', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('shelving_jobs', sa.Column('allow_unassigned_owner', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('shelving_jobs', sa.Column('allow_tiered_owner', sa.Boolean(), nullable=False, server_default='false'))
    
    # 4. Create shelving_job_containers table
    op.create_table(
        'shelving_job_containers',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('shelving_job_id', sa.Integer(), nullable=False),
        sa.Column('tray_id', sa.Integer(), nullable=True),
        sa.Column('non_tray_item_id', sa.Integer(), nullable=True),
        sa.Column('proposed_shelf_position_id', sa.Integer(), nullable=True),
        sa.Column('position_reserved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('actual_shelf_position_id', sa.Integer(), nullable=True),
        sa.Column('shelved_dt', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('was_overridden', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('override_reason', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Pending'),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('create_dt', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('update_dt', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['shelving_job_id'], ['shelving_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tray_id'], ['trays.id']),
        sa.ForeignKeyConstraint(['non_tray_item_id'], ['non_tray_items.id']),
        sa.ForeignKeyConstraint(['proposed_shelf_position_id'], ['shelf_positions.id']),
        sa.ForeignKeyConstraint(['actual_shelf_position_id'], ['shelf_positions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "(tray_id IS NOT NULL) OR (non_tray_item_id IS NOT NULL)",
            name='ck_shelving_job_container_tray_xor_non_tray'
        )
    )
    
    # 5. Create indexes for efficient querying
    op.create_index('ix_shelving_job_containers_shelving_job_id', 'shelving_job_containers', ['shelving_job_id'])
    op.create_index('ix_shelving_job_containers_tray_id', 'shelving_job_containers', ['tray_id'])
    op.create_index('ix_shelving_job_containers_non_tray_item_id', 'shelving_job_containers', ['non_tray_item_id'])
    op.create_index('ix_shelving_job_containers_status', 'shelving_job_containers', ['status'])
    op.create_index('ix_shelving_job_containers_proposed_shelf_position_id', 'shelving_job_containers', ['proposed_shelf_position_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_shelving_job_containers_proposed_shelf_position_id', table_name='shelving_job_containers')
    op.drop_index('ix_shelving_job_containers_status', table_name='shelving_job_containers')
    op.drop_index('ix_shelving_job_containers_non_tray_item_id', table_name='shelving_job_containers')
    op.drop_index('ix_shelving_job_containers_tray_id', table_name='shelving_job_containers')
    op.drop_index('ix_shelving_job_containers_shelving_job_id', table_name='shelving_job_containers')
    
    # Drop table
    op.drop_table('shelving_job_containers')
    
    # Remove columns from shelving_jobs
    op.drop_column('shelving_jobs', 'allow_tiered_owner')
    op.drop_column('shelving_jobs', 'allow_unassigned_owner')
    op.drop_column('shelving_jobs', 'allow_unassigned_size')
    op.drop_column('shelving_jobs', 'mode')
    
    # Note: Cannot remove enum values in PostgreSQL, so we leave shelving_origin and shelving_mode types
