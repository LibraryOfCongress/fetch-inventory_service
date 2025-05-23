"""Updating Request table

Revision ID: 2025_04_21_13:25:13
Revises: 7765c78711f7
Create Date: 2025-04-21 17:25:13.162815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '2025_04_21_13:25:13'
down_revision: Union[str, None] = '7765c78711f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('requests', sa.Column('requested_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key("requested_by_id_fk", 'requests', 'users',
                          ['requested_by_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("requested_by_id_fk", 'requests', type_='foreignkey')
    op.drop_column('requests', 'requested_by_id')
    # ### end Alembic commands ###
#
