import uuid
import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint

from app.models.buildings import Building


class Module(SQLModel, table=True):
    """
    Model to represent the Modules table.
    Modules belong to Buildings and have a Module Number.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "modules"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.Integer, default=None)
    building_id: int = Field(foreign_key="buildings.id", nullable=False)
    module_number: str = Field(
        max_length=50, sa_column=sa.VARCHAR, nullable=False, unique=True
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    # building in a module
    building: Building = Relationship(back_populates="modules")
    # aisles in a module
    aisles: List["Aisle"] = Relationship(back_populates="module")
