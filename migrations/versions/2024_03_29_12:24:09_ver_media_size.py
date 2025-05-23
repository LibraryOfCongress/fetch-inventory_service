"""ver_media_size

Revision ID: 2024_03_29_12:24:09
Revises: 2024_03_28_10:27:07
Create Date: 2024-03-29 11:24:09.337916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '2024_03_29_12:24:09'
down_revision: Union[str, None] = '2024_03_28_10:27:07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('verification_jobs', sa.Column('media_type_id', sa.Integer(), nullable=True))
    op.add_column('verification_jobs', sa.Column('size_class_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_verification_media_type', 'verification_jobs', 'media_types', ['media_type_id'], ['id'])
    op.create_foreign_key('fk_verification_size_class', 'verification_jobs', 'size_class', ['size_class_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('fk_verification_media_type', 'verification_jobs', type_='foreignkey')
    op.drop_constraint('fk_verification_size_class', 'verification_jobs', type_='foreignkey')
    op.drop_column('verification_jobs', 'size_class_id')
    op.drop_column('verification_jobs', 'media_type_id')
    # ### end Alembic commands ###
