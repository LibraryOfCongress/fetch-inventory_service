"""Fix module unique constraint

Revision ID: 2026_02_25_02_29_14
Revises: c1d2e3f4g5h6
Create Date: 2026-02-24 21:29:14.554002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_02_25_02_29_14'
down_revision: Union[str, None] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the generic constraint and create the composite one
    op.drop_constraint('modules_module_number_key', 'modules', type_='unique')
    op.create_unique_constraint('uq_modules_building', 'modules', ['building_id', 'module_number'])


def downgrade() -> None:
    # Revert the constraints
    op.drop_constraint('uq_modules_building', 'modules', type_='unique')
    op.create_unique_constraint('modules_module_number_key', 'modules', ['module_number'])
