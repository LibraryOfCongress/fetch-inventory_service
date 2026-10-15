"""Merge building ILS service points and export date index heads

Revision ID: 2026_08_19_merge_ils_heads
Revises: 2026_08_10_bldg_svc_pt, 2026_08_17_export_date_idx
Create Date: 2026-08-19 10:22:25.751411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa




# revision identifiers, used by Alembic.
revision: str = '2026_08_19_merge_ils_heads'
down_revision: Union[str, None] = ('2026_08_10_bldg_svc_pt', '2026_08_17_export_date_idx')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
