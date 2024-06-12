import uuid

import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint

from app.models.buildings import Building
from app.models.modules import Module
from app.models.aisle_numbers import AisleNumber


class Aisle(SQLModel, table=True):
    """
    Model to represent the aisles table.
        Aisles belong to buildings and modules simultaneously.
        Modules association is optional, Building assocation is required.
        Aisle number must be unique within a building or within a module.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "aisles"
    __table_args__ = (
        UniqueConstraint(
            "building_id", "aisle_number_id", name="uq_building_aisle_number_id"
        ),
        UniqueConstraint(
            "module_id", "aisle_number_id", name="uq_module_aisle_number_id"
        ),
        sa.CheckConstraint(
            "(module_id IS NULL AND building_id IS NOT NULL) OR (building_id IS NULL AND module_id IS NOT NULL)",
            name="ck_building_xor_module",
        ),
    )

    id: Optional[int] = Field(primary_key=True, sa_column=sa.Integer, default=None)
    sort_priority: Optional[int] = Field(
        sa_column=sa.SmallInteger, nullable=True, default=None
    )
    aisle_number_id: int = Field(
        foreign_key="aisle_numbers.id", nullable=False, default=None
    )
    module_id: Optional[int] = Field(
        foreign_key="modules.id", nullable=True, default=None
    )
    building_id: Optional[int] = Field(
        foreign_key="buildings.id", nullable=True, default=None
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    # aisle number belonging to an aisle
    aisle_number: AisleNumber = Relationship(back_populates="aisles")
    # building belonging to an aisle
    building: Building = Relationship(back_populates="aisles")
    # module belonging to an aisle
    module: Module = Relationship(back_populates="aisles")
    # sides belonging to an aisle
    sides: List["Side"] = Relationship(back_populates="aisle")
