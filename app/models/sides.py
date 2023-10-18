import uuid
import sqlalchemy as sa

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

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

    id: Optional[int] = Field(primary_key=True, sa_column=sa.Integer, default=None)
    barcode: Optional[uuid.UUID] = Field(sa_column=sa.UUID, nullable=True, default=None)
    aisle_id: int = Field(foreign_key="aisles.id", nullable=False)
    side_orientation_id: int = Field(foreign_key="side_orientations.id", nullable=False)
    create_dt: datetime = Field(
        sa_column=sa.DateTime,
        default=datetime.utcnow(),
        nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime,
        default=datetime.utcnow(),
        nullable=False
    )

    side_orientation: SideOrientation = Relationship(back_populates="sides")
    aisle: Aisle = Relationship(back_populates="sides")
