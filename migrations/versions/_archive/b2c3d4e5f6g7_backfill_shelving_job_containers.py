"""Backfill shelving_job_containers for Direct to Shelf jobs

Populates ShelvingJobContainer records for existing trays and non-tray items
that were shelved via Direct to Shelf or Verification workflows.
This enables unified container tracking across all shelving job types.

Revision ID: b2c3d4e5f6g7
Revises: 2026_01_16_18_10_00
Create Date: 2026-01-24 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = '2026_01_16_18_10_00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill ShelvingJobContainer records for existing trays
    # that were shelved via Direct or Verification workflows
    op.execute("""
        INSERT INTO shelving_job_containers 
            (shelving_job_id, tray_id, actual_shelf_position_id, status, shelved_dt, create_dt, update_dt)
        SELECT 
            t.shelving_job_id, 
            t.id, 
            t.shelf_position_id,
            'Shelved',
            COALESCE(t.shelved_dt, t.update_dt),
            NOW(),
            NOW()
        FROM trays t
        INNER JOIN shelving_jobs sj ON sj.id = t.shelving_job_id
        WHERE t.shelving_job_id IS NOT NULL
        AND t.shelf_position_id IS NOT NULL
        AND sj.origin IN ('Direct', 'Verification')
        AND NOT EXISTS (
            SELECT 1 FROM shelving_job_containers sjc 
            WHERE sjc.tray_id = t.id AND sjc.shelving_job_id = t.shelving_job_id
        )
    """)
    
    # Backfill ShelvingJobContainer records for existing non-tray items
    op.execute("""
        INSERT INTO shelving_job_containers 
            (shelving_job_id, non_tray_item_id, actual_shelf_position_id, status, shelved_dt, create_dt, update_dt)
        SELECT 
            nti.shelving_job_id, 
            nti.id, 
            nti.shelf_position_id,
            'Shelved',
            COALESCE(nti.shelved_dt, nti.update_dt),
            NOW(),
            NOW()
        FROM non_tray_items nti
        INNER JOIN shelving_jobs sj ON sj.id = nti.shelving_job_id
        WHERE nti.shelving_job_id IS NOT NULL
        AND nti.shelf_position_id IS NOT NULL
        AND sj.origin IN ('Direct', 'Verification')
        AND NOT EXISTS (
            SELECT 1 FROM shelving_job_containers sjc 
            WHERE sjc.non_tray_item_id = nti.id AND sjc.shelving_job_id = nti.shelving_job_id
        )
    """)


def downgrade() -> None:
    # Remove backfilled records (only those created by this migration)
    # Note: This is safe because the WHERE clauses match the upgrade logic
    op.execute("""
        DELETE FROM shelving_job_containers sjc
        USING shelving_jobs sj
        WHERE sjc.shelving_job_id = sj.id
        AND sj.origin IN ('Direct', 'Verification')
        AND sjc.proposed_shelf_position_id IS NULL
    """)
