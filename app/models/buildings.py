import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship


class Building(SQLModel, table=True):
    """
    Model to represent the buildings table.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "buildings"

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True), default=None)
    name: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(25), nullable=True, default=None)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    # modules in a building
    modules: List["Module"] = Relationship(back_populates="building")
    shelving_jobs: List["ShelvingJob"] = Relationship(back_populates="building")
    pick_lists: List["PickList"] = Relationship(back_populates="building")
    requests: List["Request"] = Relationship(back_populates="building")
