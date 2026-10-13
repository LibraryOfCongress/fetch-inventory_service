"""prevent duplicate verification jobs

Revision ID: a1b2c3d4e5f6
Revises: bf01acb11b05
Create Date: 2025-12-20 09:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'bf01acb11b05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraint to prevent duplicate verification jobs for the same accession job
    op.create_unique_constraint('uq_verification_jobs_accession_job_id', 'verification_jobs', ['accession_job_id'])


def downgrade() -> None:
    # Remove the unique constraint
    op.drop_constraint('uq_verification_jobs_accession_job_id', 'verification_jobs', type_='unique')
