"""add_building_ils_service_points

Revision ID: 2026_08_10_bldg_svc_pt
Revises: 2026_06_24_batch_result
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2026_08_10_bldg_svc_pt'
down_revision: Union[str, None] = '2026_06_24_batch_result'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-(Building, ILSConfiguration) FOLIO service point overrides. A
    # single ILSConfiguration.ils_service_point_id is only a per-Owner
    # default; Owners whose items are shelved across multiple physical
    # buildings (or organizations running more than one ILS integration)
    # need a service point resolved per building instead.
    op.create_table(
        'building_ils_service_points',
        sa.Column('id', sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column('building_id', sa.SmallInteger(), nullable=False),
        sa.Column('ils_configuration_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ils_service_point_id', sa.String(length=50), nullable=False),
        sa.Column('create_dt', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('update_dt', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['building_id'], ['buildings.id']),
        sa.ForeignKeyConstraint(['ils_configuration_id'], ['ils_configurations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('building_id', 'ils_configuration_id', name='uq_building_ils_configuration'),
    )


def downgrade() -> None:
    op.drop_table('building_ils_service_points')
