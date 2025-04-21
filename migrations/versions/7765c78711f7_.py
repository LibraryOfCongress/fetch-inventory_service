"""empty message

Revision ID: 7765c78711f7
Revises: 2025_04_11_17:22:40, 2025_04_13_15:19:26
Create Date: 2025-04-21 09:16:49.955573

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '7765c78711f7'
down_revision: Union[str, None] = ('2025_04_11_17:22:40', '2025_04_13_15:19:26')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
