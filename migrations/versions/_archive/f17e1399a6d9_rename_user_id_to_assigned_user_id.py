"""rename_user_id_to_assigned_user_id

Revision ID: f17e1399a6d9
Revises: 2026_02_06_07_19_46
Create Date: 2026-02-08 14:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f17e1399a6d9'
down_revision: Union[str, None] = '2026_02_06_07_19_46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename user_id to assigned_user_id in job tables using raw SQL
    op.execute('ALTER TABLE accession_jobs RENAME COLUMN user_id TO assigned_user_id')
    op.execute('ALTER TABLE verification_jobs RENAME COLUMN user_id TO assigned_user_id')
    op.execute('ALTER TABLE shelving_jobs RENAME COLUMN user_id TO assigned_user_id')
    op.execute('ALTER TABLE pick_lists RENAME COLUMN user_id TO assigned_user_id')
    
    # Drop old indexes
    op.drop_index('idx_accession_jobs_user_id', table_name='accession_jobs', if_exists=True)
    op.drop_index('idx_verification_jobs_user_id', table_name='verification_jobs', if_exists=True)
    op.drop_index('idx_shelving_jobs_user_id', table_name='shelving_jobs', if_exists=True)
    op.drop_index('idx_pick_lists_user_id', table_name='pick_lists', if_exists=True)
    
    # Create new optimized indexes
    op.create_index('idx_accession_jobs_assigned_user_status', 'accession_jobs', ['assigned_user_id', 'status'])
    op.create_index('idx_verification_jobs_assigned_user_status', 'verification_jobs', ['assigned_user_id', 'status'])
    op.create_index('idx_shelving_jobs_assigned_user_status', 'shelving_jobs', ['assigned_user_id', 'status'])
    op.create_index('idx_pick_lists_assigned_user_status', 'pick_lists', ['assigned_user_id', 'status'])
    op.create_index('idx_pick_lists_assigned_user_id', 'pick_lists', ['assigned_user_id'])


def downgrade() -> None:
    # Drop new indexes
    op.drop_index('idx_pick_lists_assigned_user_id', table_name='pick_lists')
    op.drop_index('idx_pick_lists_assigned_user_status', table_name='pick_lists')
    op.drop_index('idx_shelving_jobs_assigned_user_status', table_name='shelving_jobs')
    op.drop_index('idx_verification_jobs_assigned_user_status', table_name='verification_jobs')
    op.drop_index('idx_accession_jobs_assigned_user_status', table_name='accession_jobs')
    
    # Recreate old indexes
    op.create_index('idx_pick_lists_user_id', 'pick_lists', ['user_id'])
    op.create_index('idx_shelving_jobs_user_id', 'shelving_jobs', ['user_id'])
    op.create_index('idx_verification_jobs_user_id', 'verification_jobs', ['user_id'])
    op.create_index('idx_accession_jobs_user_id', 'accession_jobs', ['user_id'])
    
    # Rename columns back using raw SQL
    op.execute('ALTER TABLE pick_lists RENAME COLUMN assigned_user_id TO user_id')
    op.execute('ALTER TABLE shelving_jobs RENAME COLUMN assigned_user_id TO user_id')
    op.execute('ALTER TABLE verification_jobs RENAME COLUMN assigned_user_id TO user_id')
    op.execute('ALTER TABLE accession_jobs RENAME COLUMN assigned_user_id TO user_id')
