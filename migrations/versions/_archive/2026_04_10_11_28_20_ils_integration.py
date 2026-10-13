"""ils_integration

Revision ID: 2026_04_10_11_28_20
Revises: 2026_02_28_22_45_00
Create Date: 2026-04-10 07:28:20.483424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_04_10_11_28_20'
down_revision: Union[str, None] = '2026_02_28_22_45_00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ENUMS handling
    ils_sync_state_enum = postgresql.ENUM('IN_SYNC', 'PENDING_SYNC', 'SYNC_ERROR', name='ils_sync_state_enum')
    ils_sync_state_enum.create(op.get_bind(), checkfirst=True)
    
    # 2. CREATE ils_configurations
    op.create_table('ils_configurations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('adapter_type', sa.Enum('FOLIO', 'ALMA', 'CUSTOM_MIDDLEWARE', name='adapter_type_enum'), nullable=False),
        sa.Column('base_url', sa.String(length=255), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('auth_client_id', sa.String(length=255), nullable=False),
        sa.Column('auth_client_secret', sa.String(length=500), nullable=False),
        sa.Column('auth_token_url', sa.String(length=255), nullable=True),
        sa.Column('expected_shelved_status', sa.String(length=100), nullable=False),
        sa.Column('expected_refile_status', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('enable_accession_hook', sa.Boolean(), nullable=False),
        sa.Column('enable_shelving_hook', sa.Boolean(), nullable=False),
        sa.Column('enable_refile_hook', sa.Boolean(), nullable=False),
        sa.Column('enable_requests_hook', sa.Boolean(), nullable=False),
        sa.Column('enable_jit_metadata_hook', sa.Boolean(), nullable=False),
        sa.Column('create_dt', sa.DateTime(timezone=True), nullable=False),
        sa.Column('update_dt', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ils_configurations_name'), 'ils_configurations', ['name'], unique=True)

    # 3. CREATE ils_sync_errors
    op.create_table('ils_sync_errors',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('item_barcode', sa.String(length=100), nullable=False),
        sa.Column('workflow_action', sa.Enum('ACCESSION', 'SHELVING', 'REFILE', 'REQUEST_SYNC', name='workflow_action_enum'), nullable=False),
        sa.Column('error_message', sa.String(length=1000), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'RESOLVED', 'IGNORED', name='ils_sync_status_enum'), nullable=False),
        sa.Column('resolved_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('create_dt', sa.DateTime(timezone=True), nullable=False),
        sa.Column('update_dt', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ils_sync_errors_item_barcode'), 'ils_sync_errors', ['item_barcode'], unique=False)

    # 4. ALTER items, non_tray_items
    op.add_column('items', sa.Column('ils_sync_state', ils_sync_state_enum, nullable=True))
    op.add_column('non_tray_items', sa.Column('ils_sync_state', ils_sync_state_enum, nullable=True))

    # 5. ALTER owners
    op.add_column('owners', sa.Column('ils_configuration_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_owners_ils_configuration_id', 'owners', 'ils_configurations', ['ils_configuration_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_owners_ils_configuration_id', 'owners', type_='foreignkey')
    op.drop_column('owners', 'ils_configuration_id')
    op.drop_column('non_tray_items', 'ils_sync_state')
    op.drop_column('items', 'ils_sync_state')

    ils_sync_state_enum = postgresql.ENUM('IN_SYNC', 'PENDING_SYNC', 'SYNC_ERROR', name='ils_sync_state_enum')
    ils_sync_state_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_index(op.f('ix_ils_sync_errors_item_barcode'), table_name='ils_sync_errors')
    op.drop_table('ils_sync_errors')
    op.drop_index(op.f('ix_ils_configurations_name'), table_name='ils_configurations')
    op.drop_table('ils_configurations')
