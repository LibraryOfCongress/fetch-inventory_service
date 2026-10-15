"""add scheduled exports

Revision ID: 2026_05_04_scheduled_exports
Revises: 9c973da1bd66
Create Date: 2026-05-04 17:33:13.927534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2026_05_04_scheduled_exports'
down_revision: Union[str, None] = '9c973da1bd66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('scheduled_exports',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('dataset', sa.String(length=50), nullable=False),
    sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('schedule_type', sa.Enum('once', 'recurring', name='schedule_type'), nullable=True),
    sa.Column('frequency', sa.Enum('daily', 'weekly', 'monthly', name='export_frequency'), nullable=True),
    sa.Column('retention_days', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('create_dt', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column('update_dt', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('export_history',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('scheduled_export_id', sa.Integer(), nullable=True),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('file_path', sa.String(length=512), nullable=False),
    sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='export_status'), nullable=True),
    sa.Column('error_message', sa.String(length=1000), nullable=True),
    sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('create_dt', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column('update_dt', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.ForeignKeyConstraint(['scheduled_export_id'], ['scheduled_exports.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('export_history')
    op.drop_table('scheduled_exports')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS schedule_type")
    op.execute("DROP TYPE IF EXISTS export_frequency")
    op.execute("DROP TYPE IF EXISTS export_status")
