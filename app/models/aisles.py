import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint


from app.models.modules import Module
from app.models.aisle_numbers import AisleNumber


class Aisle(SQLModel, table=True):
    """
    Model to represent the aisles table.
        Aisles belong to modules simultaneously.
        Modules association is required.
        Aisle number must be unique within a module.

    id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "aisles"
    __table_args__ = (
        UniqueConstraint(
            "module_id", "aisle_number_id", name="uq_module_aisle_number_id"
        ),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.Integer, primary_key=True), default=None)
    sort_priority: Optional[int] = Field(
        sa_column=sa.Column(sa.SmallInteger, nullable=True, default=None)
    )
    aisle_number_id: int = Field(
        foreign_key="aisle_numbers.id", nullable=False, default=None
    )
    module_id: Optional[int] = Field(
        foreign_key="modules.id", nullable=True, default=None
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    # aisle number belonging to an aisle
    aisle_number: AisleNumber = Relationship(back_populates="aisles")
    # module belonging to an aisle
    module: Module = Relationship(back_populates="aisles")
    # sides belonging to an aisle
    sides: List["Side"] = Relationship(back_populates="aisle")
