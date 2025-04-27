import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint


class SideOrientation(SQLModel, table=True):
    """
    Model to represent the side orientations (Left, Right).
        SideOrientation is a Side configuration in an Aisle.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "side_orientations"
    __table_args__ = (UniqueConstraint("name", name="uq_side_orientation_name"),)

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True), default=None)
    name: str = Field(sa_column=sa.Column(sa.VARCHAR(5), nullable=False, index=True))
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    # Sides in xyz orientation
    sides: List["Side"] = Relationship(back_populates="side_orientation")
