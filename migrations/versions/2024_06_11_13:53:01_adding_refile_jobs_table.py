"""Adding Refile Jobs table

Revision ID: 2024_06_11_13:53:01
Revises: 2024_06_10_09:05:29
Create Date: 2024-06-11 17:53:01.608412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

from app.models.refile_jobs import RefileJobStatus

# revision identifiers, used by Alembic.
revision: str = "2024_06_11_13:53:01"
down_revision: Union[str, None] = "2024_06_10_09:05:29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "refile_jobs",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("assigned_user_id", sa.Integer(), nullable=True),
        sa.Column("run_time", sa.Interval(), nullable=True),
        sa.Column("create_dt", sa.DateTime(), nullable=False),
        sa.Column("update_dt", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "refile_non_tray_items",
        sa.Column("non_tray_item_id", sa.Integer(), nullable=False),
        sa.Column("refile_job_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["non_tray_item_id"],
            ["non_tray_items.id"],
        ),
        sa.ForeignKeyConstraint(
            ["refile_job_id"],
            ["refile_jobs.id"],
        ),
        sa.PrimaryKeyConstraint("non_tray_item_id"),
        sa.UniqueConstraint(
            "non_tray_item_id",
            "refile_job_id",
            name="uq_non_tray_item_id_refile_job_id",
        ),
    )
    op.create_table(
        "refile_items",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("refile_job_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
        ),
        sa.ForeignKeyConstraint(
            ["refile_job_id"],
            ["refile_jobs.id"],
        ),
        sa.PrimaryKeyConstraint("item_id", "refile_job_id"),
        sa.UniqueConstraint(
            "item_id", "refile_job_id", name="uq_item_id_refile_job_id"
        ),
    )

    # Create enum for 'status' column in 'refile_jobs'
    refile_job_enum = sa.Enum(RefileJobStatus, name="refile_job_status_enum")
    refile_job_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "refile_jobs",
        sa.Column(
            "status",
            refile_job_enum,
            nullable=True,
            server_default=RefileJobStatus.Created,
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("refile_items")
    op.drop_table("refile_non_tray_items")
    op.drop_table("refile_jobs")
    # ### end Alembic commands ###
