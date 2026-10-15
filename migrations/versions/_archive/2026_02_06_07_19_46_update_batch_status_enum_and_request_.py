"""update_batch_status_enum_and_request_index

Revision ID: 2026_02_06_07_19_46
Revises: 70d0a34dcda3
Create Date: 2026-02-06 07:19:46.982457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_02_06_07_19_46'
down_revision: Union[str, None] = '70d0a34dcda3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update BatchUploadStatus Enum: Add 'Uploaded'
    # Use autocommit block for ALTER TYPE which cannot run inside a transaction block in some PG versions
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT 1 FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid WHERE pg_type.typname = 'batch_upload_status_enum' AND pg_enum.enumlabel = 'Uploaded'")).scalar()
    if not res:
        op.execute("COMMIT")
        op.execute("ALTER TYPE batch_upload_status_enum ADD VALUE 'Uploaded'")
        op.execute("BEGIN")

    # 2. Migrate existing data: 'Completed' (old meaning) -> 'Uploaded'
    # Doing this allows 'Completed' to be reused for the new meaning (All Requests Done)
    op.execute("UPDATE batch_uploads SET status = 'Uploaded' WHERE status = 'Completed'")

    # 3. Add Index to requests
    op.create_index(op.f('ix_requests_batch_upload_id'), 'requests', ['batch_upload_id'], unique=False)


def downgrade() -> None:
    # 1. Drop Index
    op.drop_index(op.f('ix_requests_batch_upload_id'), table_name='requests')

    # 2. Revert data: 'Uploaded' -> 'Completed'
    op.execute("UPDATE batch_uploads SET status = 'Completed' WHERE status = 'Uploaded'")
    
    # Note: We cannot easily remove 'Uploaded' from the Enum type in Postgres without full recreation.
    # We leave the value in the type, but no rows will use it.
