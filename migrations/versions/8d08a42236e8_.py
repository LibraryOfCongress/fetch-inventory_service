"""empty message

Revision ID: 8d08a42236e8
Revises: 2025_04_21_13:25:13, 2025_04_21_20:43:30
Create Date: 2025-04-22 18:10:20.150338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '8d08a42236e8'
down_revision: Union[str, None] = ('2025_04_21_13:25:13', '2025_04_21_20:43:30')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
