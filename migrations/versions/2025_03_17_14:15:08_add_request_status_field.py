"""Add Request Status Field

Revision ID: 2025_03_17_14:15:08
Revises: 2025_03_04_18:05:54
Create Date: 2025-03-17 18:15:08.960916

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

from app.models.requests import RequestStatus


# revision identifiers, used by Alembic.
revision: str = "2025_03_17_14:15:08"
down_revision: Union[str, None] = "2025_03_04_18:05:54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    request_status_enum = postgresql.ENUM(RequestStatus, name="request_status")
    request_status_enum.create(op.get_bind(), checkfirst=True)
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "requests",
        sa.Column(
            "status",
            request_status_enum,
            nullable=False,
            server_default=RequestStatus.New,
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("requests", "status")
    # ### end Alembic commands ###
