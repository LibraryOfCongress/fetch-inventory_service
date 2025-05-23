"""Removing scanned for refile

Revision ID: 2024_06_18_14:45:27
Revises: 2024_06_18_13:47:03
Create Date: 2024-06-18 18:45:27.189228

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2024_06_18_14:45:27"
down_revision: Union[str, None] = "2024_06_18_13:47:03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("items", "scanned_for_refile_dt")
    op.drop_column("items", "scanned_for_refile")
    op.drop_column("non_tray_items", "scanned_for_refile_dt")
    op.drop_column("non_tray_items", "scanned_for_refile")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "non_tray_items",
        sa.Column(
            "scanned_for_refile", sa.BOOLEAN(), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "non_tray_items",
        sa.Column(
            "scanned_for_refile_dt",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "items",
        sa.Column(
            "scanned_for_refile", sa.BOOLEAN(), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "items",
        sa.Column(
            "scanned_for_refile_dt",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
    )
    # ### end Alembic commands ###
