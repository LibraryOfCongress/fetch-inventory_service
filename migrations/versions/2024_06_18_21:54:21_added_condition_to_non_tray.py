"""Added condition to non tray

Revision ID: 2024_06_18_21:54:21
Revises: 2024_06_18_14:45:27
Create Date: 2024-06-19 01:54:21.691981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2024_06_18_21:54:21"
down_revision: Union[str, None] = "2024_06_18_14:45:27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "non_tray_items",
        sa.Column(
            "condition", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("non_tray_items", "condition")
    # ### end Alembic commands ###
