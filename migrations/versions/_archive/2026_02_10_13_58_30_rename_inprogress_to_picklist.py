"""Rename InProgress to PickList

Revision ID: 2026_02_10_13_58_30
Revises: 2026_02_08_11_35_00
Create Date: 2026-02-10 13:58:30.465130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_10_13_58_30'
down_revision: Union[str, None] = '2026_02_08_11_35_00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename 'InProgress' to 'PickList' in the request_status enum
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT 1 FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid WHERE pg_type.typname = 'request_status' AND pg_enum.enumlabel = 'InProgress'")).scalar()
    if res:
        # PostgreSQL doesn't allow ALTER TYPE inside a transaction block gracefully if there are errors,
        # but since Alembic runs inside a transaction, we commit first, run the alter type, and start a new transaction.
        op.execute("COMMIT")
        op.execute("ALTER TYPE request_status RENAME VALUE 'InProgress' TO 'PickList'")
        op.execute("BEGIN")


def downgrade() -> None:
    # Rename 'PickList' back to 'InProgress'
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT 1 FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid WHERE pg_type.typname = 'request_status' AND pg_enum.enumlabel = 'PickList'")).scalar()
    if res:
        op.execute("COMMIT")
        op.execute("ALTER TYPE request_status RENAME VALUE 'PickList' TO 'InProgress'")
        op.execute("BEGIN")
