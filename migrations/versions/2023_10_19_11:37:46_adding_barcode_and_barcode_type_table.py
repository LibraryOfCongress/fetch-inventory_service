"""Adding Barcode and Barcode Type table

Revision ID: 2023_10_19_11:37:46
Revises: 2023_10_18_07:44:56
Create Date: 2023-10-19 15:37:46.182038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "2023_10_19_11:37:46"
down_revision: Union[str, None] = "2023_10_18_07:44:56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "barcode_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "name",
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=False,
            unique=True,
        ),
        sa.Column("update_dt", sa.DateTime(), nullable=False),
        sa.Column("create_dt", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "barcodes",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column(
            "value",
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=False,
            unique=True,
        ),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("update_dt", sa.DateTime(), nullable=False),
        sa.Column("create_dt", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["type_id"],
            ["barcode_types.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_unique_constraint(None, "barcode_types", ["name"])
    op.create_unique_constraint(None, "barcodes", ["value"])
    op.add_column(
        "aisles", sa.Column("barcode_id", sa.dialects.postgresql.UUID(), nullable=True)
    )
    op.create_foreign_key(None, "aisles", "barcodes", ["barcode_id"], ["id"])
    op.drop_column("aisles", "barcode")
    op.add_column(
        "buildings",
        sa.Column("barcode_id", sa.dialects.postgresql.UUID(), nullable=True),
    )
    op.create_foreign_key(None, "buildings", "barcodes", ["barcode_id"], ["id"])
    op.drop_column("buildings", "barcode")
    op.add_column(
        "modules", sa.Column("barcode_id", sa.dialects.postgresql.UUID(), nullable=True)
    )
    op.create_foreign_key(None, "modules", "barcodes", ["barcode_id"], ["id"])
    op.drop_column("modules", "barcode")
    op.add_column(
        "sides", sa.Column("barcode_id", sa.dialects.postgresql.UUID(), nullable=True)
    )
    op.create_foreign_key(None, "sides", "barcodes", ["barcode_id"], ["id"])
    op.drop_column("sides", "barcode")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "sides", sa.Column("barcode", sa.UUID(), autoincrement=False, nullable=True)
    )
    op.drop_constraint(None, "sides", type_="foreignkey")
    op.drop_column("sides", "barcode_id")
    op.add_column(
        "modules", sa.Column("barcode", sa.UUID(), autoincrement=False, nullable=True)
    )
    op.drop_constraint(None, "modules", type_="foreignkey")
    op.drop_column("modules", "barcode_id")
    op.add_column(
        "buildings", sa.Column("barcode", sa.UUID(), autoincrement=False, nullable=True)
    )
    op.drop_constraint(None, "buildings", type_="foreignkey")
    op.drop_column("buildings", "barcode_id")
    op.add_column(
        "aisles", sa.Column("barcode", sa.UUID(), autoincrement=False, nullable=True)
    )
    op.drop_constraint(None, "aisles", type_="foreignkey")
    op.drop_column("aisles", "barcode_id")
    op.drop_table("barcodes")
    op.drop_table("barcode_types")
    # ### end Alembic commands ###
