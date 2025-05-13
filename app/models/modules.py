import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship

from app.models.buildings import Building


class Module(SQLModel, table=True):
    """
    Model to represent the Modules table.
    Modules belong to Buildings and have a Module Number.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "modules"

    id: Optional[int] = Field(sa_column=sa.Column(sa.Integer, primary_key=True), default=None)
    building_id: int = Field(foreign_key="buildings.id", nullable=False)
    module_number: str = Field(
        sa_column=sa.Column(sa.VARCHAR(50), nullable=True, unique=True)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    # building in a module
    building: Building = Relationship(back_populates="modules")
    # aisles in a module
    aisles: List["Aisle"] = Relationship(back_populates="module")
