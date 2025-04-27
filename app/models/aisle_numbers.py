import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship


class AisleNumber(SQLModel, table=True):
    """
    Model to represent the Aisle Numbers table.
    Aisle Numbers are unique within the table, but may be re-used
    by different Modules and Buildings.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "aisle_numbers"

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True), default=None)
    number: int = Field(
        sa_column=sa.Column(sa.SmallInteger, nullable=False, unique=True)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    # aisles assigned this aisle number
    aisles: List["Aisle"] = Relationship(back_populates="aisle_number")
