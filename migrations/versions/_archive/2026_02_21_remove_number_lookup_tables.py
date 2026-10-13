"""Remove number lookup tables and use direct integer columns

Revision ID: c1d2e3f4g5h6
Revises: 2026_02_21_01_32_09
Create Date: 2026-02-21 12:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = '2026_02_21_01_32_09'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===== STEP 1: Add new direct integer columns =====
    op.add_column('aisles', sa.Column('aisle_number', sa.SmallInteger(), nullable=True))
    op.add_column('ladders', sa.Column('ladder_number', sa.SmallInteger(), nullable=True))
    op.add_column('shelves', sa.Column('shelf_number', sa.SmallInteger(), nullable=True))
    op.add_column('shelf_positions', sa.Column('position_number', sa.SmallInteger(), nullable=True))

    # ===== STEP 2: Populate from lookup table joins =====
    op.execute("""
        UPDATE aisles 
        SET aisle_number = an.number 
        FROM aisle_numbers an 
        WHERE aisles.aisle_number_id = an.id
    """)

    op.execute("""
        UPDATE ladders 
        SET ladder_number = ln.number 
        FROM ladder_numbers ln 
        WHERE ladders.ladder_number_id = ln.id
    """)

    op.execute("""
        UPDATE shelves 
        SET shelf_number = sn.number 
        FROM shelf_numbers sn 
        WHERE shelves.shelf_number_id = sn.id
    """)

    op.execute("""
        UPDATE shelf_positions 
        SET position_number = spn.number 
        FROM shelf_position_numbers spn 
        WHERE shelf_positions.shelf_position_number_id = spn.id
    """)

    # ===== STEP 3: Set NOT NULL on new columns =====
    op.alter_column('aisles', 'aisle_number', nullable=False)
    op.alter_column('ladders', 'ladder_number', nullable=False)
    op.alter_column('shelves', 'shelf_number', nullable=False)
    op.alter_column('shelf_positions', 'position_number', nullable=False)

    # ===== STEP 4: Drop old unique constraints =====
    op.drop_constraint('uq_module_aisle_number_id', 'aisles', type_='unique')
    op.drop_constraint('uq_side_id_ladder_number_id', 'ladders', type_='unique')
    op.drop_constraint('uq_ladder_id_shelf_number_id', 'shelves', type_='unique')
    op.drop_constraint('uq_shelf_id_shelf_position_number_id', 'shelf_positions', type_='unique')

    # ===== STEP 5: Drop old FK columns =====
    op.drop_column('aisles', 'aisle_number_id')
    op.drop_column('ladders', 'ladder_number_id')
    op.drop_column('shelves', 'shelf_number_id')
    op.drop_column('shelf_positions', 'shelf_position_number_id')

    # ===== STEP 6: Create new unique constraints =====
    op.create_unique_constraint('uq_module_aisle_number', 'aisles', ['module_id', 'aisle_number'])
    op.create_unique_constraint('uq_side_id_ladder_number', 'ladders', ['side_id', 'ladder_number'])
    op.create_unique_constraint('uq_ladder_id_shelf_number', 'shelves', ['ladder_id', 'shelf_number'])
    op.create_unique_constraint('uq_shelf_id_position_number', 'shelf_positions', ['shelf_id', 'position_number'])

    # ===== STEP 7: Drop lookup tables =====
    op.drop_table('aisle_numbers')
    op.drop_table('ladder_numbers')
    op.drop_table('shelf_numbers')
    op.drop_table('shelf_position_numbers')


def downgrade() -> None:
    # ===== Recreate lookup tables =====
    op.create_table('aisle_numbers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('number', sa.Integer(), nullable=False, unique=True),
        sa.Column('create_dt', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('update_dt', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table('ladder_numbers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('number', sa.Integer(), nullable=False, unique=True),
        sa.Column('create_dt', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('update_dt', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table('shelf_numbers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('number', sa.Integer(), nullable=False, unique=True),
        sa.Column('create_dt', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('update_dt', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table('shelf_position_numbers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('number', sa.Integer(), nullable=False, unique=True),
        sa.Column('create_dt', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('update_dt', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed the lookup tables with numbers 1-100 (or 1-25 for positions)
    for i in range(1, 101):
        op.execute(f"INSERT INTO aisle_numbers (number) VALUES ({i})")
        op.execute(f"INSERT INTO ladder_numbers (number) VALUES ({i})")
        op.execute(f"INSERT INTO shelf_numbers (number) VALUES ({i})")
    for i in range(1, 26):
        op.execute(f"INSERT INTO shelf_position_numbers (number) VALUES ({i})")

    # Re-add FK columns
    op.add_column('aisles', sa.Column('aisle_number_id', sa.Integer(), nullable=True))
    op.add_column('ladders', sa.Column('ladder_number_id', sa.Integer(), nullable=True))
    op.add_column('shelves', sa.Column('shelf_number_id', sa.Integer(), nullable=True))
    op.add_column('shelf_positions', sa.Column('shelf_position_number_id', sa.Integer(), nullable=True))

    # Populate FK columns from direct integer columns
    op.execute("UPDATE aisles SET aisle_number_id = (SELECT id FROM aisle_numbers WHERE number = aisles.aisle_number)")
    op.execute("UPDATE ladders SET ladder_number_id = (SELECT id FROM ladder_numbers WHERE number = ladders.ladder_number)")
    op.execute("UPDATE shelves SET shelf_number_id = (SELECT id FROM shelf_numbers WHERE number = shelves.shelf_number)")
    op.execute("UPDATE shelf_positions SET shelf_position_number_id = (SELECT id FROM shelf_position_numbers WHERE number = shelf_positions.position_number)")

    # Set NOT NULL
    op.alter_column('aisles', 'aisle_number_id', nullable=False)
    op.alter_column('ladders', 'ladder_number_id', nullable=False)
    op.alter_column('shelves', 'shelf_number_id', nullable=False)
    op.alter_column('shelf_positions', 'shelf_position_number_id', nullable=False)

    # Drop new unique constraints
    op.drop_constraint('uq_module_aisle_number', 'aisles', type_='unique')
    op.drop_constraint('uq_side_id_ladder_number', 'ladders', type_='unique')
    op.drop_constraint('uq_ladder_id_shelf_number', 'shelves', type_='unique')
    op.drop_constraint('uq_shelf_id_position_number', 'shelf_positions', type_='unique')

    # Drop new direct columns
    op.drop_column('aisles', 'aisle_number')
    op.drop_column('ladders', 'ladder_number')
    op.drop_column('shelves', 'shelf_number')
    op.drop_column('shelf_positions', 'position_number')

    # Recreate old unique constraints
    op.create_unique_constraint('uq_module_aisle_number_id', 'aisles', ['module_id', 'aisle_number_id'])
    op.create_unique_constraint('uq_side_id_ladder_number_id', 'ladders', ['side_id', 'ladder_number_id'])
    op.create_unique_constraint('uq_ladder_id_shelf_number_id', 'shelves', ['ladder_id', 'shelf_number_id'])
    op.create_unique_constraint('uq_shelf_id_shelf_position_number_id', 'shelf_positions', ['shelf_id', 'shelf_position_number_id'])

    # Create FK constraints
    op.create_foreign_key(None, 'aisles', 'aisle_numbers', ['aisle_number_id'], ['id'])
    op.create_foreign_key(None, 'ladders', 'ladder_numbers', ['ladder_number_id'], ['id'])
    op.create_foreign_key(None, 'shelves', 'shelf_numbers', ['shelf_number_id'], ['id'])
    op.create_foreign_key(None, 'shelf_positions', 'shelf_position_numbers', ['shelf_position_number_id'], ['id'])
