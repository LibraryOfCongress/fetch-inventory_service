"""remove physical location strings

Revision ID: remove_location
Revises: 2026_02_25_02_29_14
Create Date: 2026-02-27 21:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'remove_location'
down_revision = '2026_02_25_02_29_14'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Drop from shelves
    op.drop_column('shelves', 'location')
    op.drop_column('shelves', 'internal_location')

    # Drop from shelf_positions
    op.drop_column('shelf_positions', 'location')
    op.drop_column('shelf_positions', 'internal_location')

def downgrade() -> None:
    # Add back to shelves
    op.add_column('shelves', sa.Column('location', sa.String(length=175), nullable=True))
    op.add_column('shelves', sa.Column('internal_location', sa.String(length=200), nullable=True))
    op.create_unique_constraint('uq_location_internal_location', 'shelves', ['location', 'internal_location'])

    # Add back to shelf_positions
    op.add_column('shelf_positions', sa.Column('location', sa.String(length=175), nullable=True))
    op.add_column('shelf_positions', sa.Column('internal_location', sa.String(length=200), nullable=True))
