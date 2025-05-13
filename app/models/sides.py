import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint

from app.models.aisles import Aisle
from app.models.side_orientations import SideOrientation


class Side(SQLModel, table=True):
    """
    Model to represent the sides table.
        Sides belong to Aisles and have an Orientation.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "sides"
    __table_args__ = (
        UniqueConstraint(
            "aisle_id", "side_orientation_id", name="uq_aisle_id_side_orientation_id"
        ),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.Integer, primary_key=True), default=None)
    aisle_id: int = Field(foreign_key="aisles.id", nullable=False)
    side_orientation_id: int = Field(foreign_key="side_orientations.id", nullable=False)
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    # side orientation belonging to a side
    side_orientation: SideOrientation = Relationship(back_populates="sides")
    # aisle in which the side is located
    aisle: Aisle = Relationship(back_populates="sides")
    # Ladders on a side (test for plurality on back_populates)
    ladders: List["Ladder"] = Relationship(back_populates="side")
