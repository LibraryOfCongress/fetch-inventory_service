"""App-level audit logging: add new columns, truncate old data, drop triggers

Revision ID: 2026_02_28_22_45_00
Revises: remove_location
Create Date: 2026-02-28 22:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_28_22_45_00'
down_revision: Union[str, None] = 'remove_location'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Truncate existing audit data (clean slate)
    op.execute("TRUNCATE TABLE audit_log")

    # 2. Add new columns for application-level audit logging
    op.add_column('audit_log', sa.Column('event_type', sa.String(100), nullable=True))
    op.add_column('audit_log', sa.Column('description', sa.String(500), nullable=True))
    op.add_column('audit_log', sa.Column('entity_type', sa.String(50), nullable=True))
    op.add_column('audit_log', sa.Column('entity_id', sa.String(50), nullable=True))
    op.add_column('audit_log', sa.Column('job_type', sa.String(50), nullable=True))
    op.add_column('audit_log', sa.Column('job_id', sa.String(50), nullable=True))

    # 3. Make previously NOT NULL columns nullable (since app-level rows
    #    won't always have table_name/record_id/operation_type/updated_by)
    op.alter_column('audit_log', 'table_name', nullable=True)
    op.alter_column('audit_log', 'record_id', nullable=True)
    op.alter_column('audit_log', 'operation_type', nullable=True)
    op.alter_column('audit_log', 'updated_by', nullable=True)
    op.alter_column('audit_log', 'updated_by_user_id', nullable=True)
    op.alter_column('audit_log', 'updated_at', nullable=True)

    # 4. Add indexes for efficient querying
    op.create_index('ix_audit_log_entity', 'audit_log', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_log_job', 'audit_log', ['job_type', 'job_id'])
    op.create_index('ix_audit_log_event_type', 'audit_log', ['event_type'])

    # 5. Drop all PostgreSQL triggers and the trigger function
    op.execute("DROP TRIGGER IF EXISTS audit_log_trigger_items ON items")
    op.execute("DROP TRIGGER IF EXISTS audit_log_trigger_non_tray_items ON non_tray_items")
    op.execute("DROP TRIGGER IF EXISTS audit_log_trigger_trays ON trays")
    op.execute("DROP TRIGGER IF EXISTS audit_log_trigger_accession_jobs ON accession_jobs")
    op.execute("DROP TRIGGER IF EXISTS audit_log_trigger_pick_lists ON pick_lists")
    op.execute("DROP TRIGGER IF EXISTS audit_log_trigger_refile_jobs ON refile_jobs")
    op.execute("DROP TRIGGER IF EXISTS audit_log_trigger_shelving_jobs ON shelving_jobs")
    op.execute("DROP TRIGGER IF EXISTS audit_log_trigger_verification_jobs ON verification_jobs")
    op.execute("DROP TRIGGER IF EXISTS audit_log_trigger_withdraw_jobs ON withdraw_jobs")
    op.execute("DROP FUNCTION IF EXISTS audit_trigger() CASCADE")


def downgrade() -> None:
    # Drop new indexes
    op.drop_index('ix_audit_log_event_type', table_name='audit_log')
    op.drop_index('ix_audit_log_job', table_name='audit_log')
    op.drop_index('ix_audit_log_entity', table_name='audit_log')

    # Revert nullable changes
    op.alter_column('audit_log', 'updated_at', nullable=False)
    op.alter_column('audit_log', 'updated_by_user_id', nullable=False)
    op.alter_column('audit_log', 'updated_by', nullable=False)
    op.alter_column('audit_log', 'operation_type', nullable=False)
    op.alter_column('audit_log', 'record_id', nullable=False)
    op.alter_column('audit_log', 'table_name', nullable=False)

    # Drop new columns
    op.drop_column('audit_log', 'job_id')
    op.drop_column('audit_log', 'job_type')
    op.drop_column('audit_log', 'entity_id')
    op.drop_column('audit_log', 'entity_type')
    op.drop_column('audit_log', 'description')
    op.drop_column('audit_log', 'event_type')
