"""computed_shelf_space

Revision ID: 2024_12_21_23:24:21
Revises: 2024_12_16_20:53:02
Create Date: 2024-12-21 23:24:21.022853

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '2024_12_21_23:24:21'
down_revision: Union[str, None] = '2024_12_19_16:50:19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('shelves', 'available_space')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('shelves', sa.Column('available_space', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
    # ### end Alembic commands ###
