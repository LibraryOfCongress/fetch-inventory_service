"""add_assigned_status_to_all_job_types

Revision ID: 2026_02_08_11_35_00
Revises: f17e1399a6d9
Create Date: 2026-02-08 11:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_08_11_35_00'
down_revision: Union[str, None] = 'f17e1399a6d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add 'Assigned' status to all job type enums.
    
    CRITICAL: PostgreSQL enum values must be COMMITTED before they can be used.
    We must add all enum values first, commit, then update the data.
    """
    
    # Get the connection to manually commit after enum additions
    connection = op.get_bind()
    
    # Phase 1: Add all enum values (these must be committed before use)
    # Add 'Assigned' to accession_status enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'Assigned' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'accession_status'
                )
            ) THEN
                ALTER TYPE accession_status ADD VALUE 'Assigned' AFTER 'Created';
            END IF;
        END
        $$;
    """)
    
    # Add 'Assigned' to verification_status enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'Assigned' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'verification_status'
                )
            ) THEN
                ALTER TYPE verification_status ADD VALUE 'Assigned' AFTER 'Created';
            END IF;
        END
        $$;
    """)
    
    # Add 'Assigned' to shelving_status enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'Assigned' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'shelving_status'
                )
            ) THEN
                ALTER TYPE shelving_status ADD VALUE 'Assigned' AFTER 'Created';
            END IF;
        END
        $$;
    """)
    
    # Add 'Assigned' to pick_list_status enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'Assigned' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'pick_list_status'
                )
            ) THEN
                ALTER TYPE pick_list_status ADD VALUE 'Assigned' AFTER 'Created';
            END IF;
        END
        $$;
    """)
    
    # Add 'Assigned' to refile_job_status_enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'Assigned' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'refile_job_status_enum'
                )
            ) THEN
                ALTER TYPE refile_job_status_enum ADD VALUE 'Assigned' AFTER 'Created';
            END IF;
        END
        $$;
    """)
    
    # Add 'Assigned' to withdraw_status enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'Assigned' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'withdraw_status'
                )
            ) THEN
                ALTER TYPE withdraw_status ADD VALUE 'Assigned' AFTER 'Created';
            END IF;
        END
        $$;
    """)
    
    # CRITICAL: Commit the enum additions before using them
    connection.commit()
    
    # Phase 2: Now we can safely use the new enum values
    # Data migration: Update existing jobs with assigned_user_id to 'Assigned' status
    # Only update jobs that are currently in 'Created' status and have a user assigned
    op.execute("""
        UPDATE accession_jobs 
        SET status = 'Assigned' 
        WHERE assigned_user_id IS NOT NULL 
          AND status = 'Created';
    """)
    
    op.execute("""
        UPDATE verification_jobs 
        SET status = 'Assigned' 
        WHERE assigned_user_id IS NOT NULL 
          AND status = 'Created';
    """)
    
    op.execute("""
        UPDATE shelving_jobs 
        SET status = 'Assigned' 
        WHERE assigned_user_id IS NOT NULL 
          AND status = 'Created';
    """)
    
    op.execute("""
        UPDATE pick_lists 
        SET status = 'Assigned' 
        WHERE assigned_user_id IS NOT NULL 
          AND status = 'Created';
    """)
    
    op.execute("""
        UPDATE refile_jobs 
        SET status = 'Assigned' 
        WHERE assigned_user_id IS NOT NULL 
          AND status = 'Created';
    """)
    
    op.execute("""
        UPDATE withdraw_jobs 
        SET status = 'Assigned' 
        WHERE assigned_user_id IS NOT NULL 
          AND status = 'Created';
    """)


def downgrade() -> None:
    """
    Rollback: Remove 'Assigned' status from all job type enums.
    
    WARNING: This will convert all 'Assigned' jobs back to 'Created'.
    Data will be preserved but status information will be lost.
    """
    
    # Convert all 'Assigned' jobs back to 'Created' before removing enum value
    op.execute("UPDATE accession_jobs SET status = 'Created' WHERE status = 'Assigned';")
    op.execute("UPDATE verification_jobs SET status = 'Created' WHERE status = 'Assigned';")
    op.execute("UPDATE shelving_jobs SET status = 'Created' WHERE status = 'Assigned';")
    op.execute("UPDATE pick_lists SET status = 'Created' WHERE status = 'Assigned';")
    op.execute("UPDATE refile_jobs SET status = 'Created' WHERE status = 'Assigned';")
    op.execute("UPDATE withdraw_jobs SET status = 'Created' WHERE status = 'Assigned';")
    
    # Note: PostgreSQL does not support removing enum values directly
    # The enum values will remain in the database but won't be used by the application
    # To fully remove them, you would need to recreate the enum types, which is complex
    # and requires dropping/recreating all dependent columns
    
    # For safety, we'll leave the enum values in place but document that they're unused
    pass
