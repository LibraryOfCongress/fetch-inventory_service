import uuid
import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint

from app.models.buildings import Building
from app.models.module_numbers import ModuleNumber


class Module(SQLModel, table=True):
    """
    Model to represent the Modules table.
    Modules belong to Buildings and have a Module Number.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "modules"
    __table_args__ = (
        UniqueConstraint("building_id", "module_number_id", name="uq_building_id_module_number_id"),
    )

    id: Optional[int] = Field(primary_key=True, sa_column=sa.Integer, default=None)
    barcode: Optional[uuid.UUID] = Field(sa_column=sa.UUID, nullable=True, default=None)
    building_id: int = Field(foreign_key="buildings.id", nullable=False)
    module_number_id: int = Field(
        foreign_key="module_numbers.id",
        nullable=False,
        default=None
    )
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

    building: Building = Relationship(back_populates="modules")
    module_number: ModuleNumber = Relationship(back_populates="modules")
    # aisles in a module
    aisles: List['Aisle'] = Relationship(back_populates="module")

