from typing import Optional, List
from datetime import datetime, timezone

import sqlalchemy as sa

from pydantic import condecimal
from sqlmodel import SQLModel, Field, Relationship


class SizeClass(SQLModel, table=True):
    """
    Model to represent the Size Class table.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "size_class"

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True))
    name: str = Field(sa_column=sa.Column(sa.VARCHAR(50), nullable=False, unique=True))
    short_name: str = Field(
        sa_column=sa.Column(sa.VARCHAR(11), nullable=False, unique=True)
    )
    height: condecimal(decimal_places=2) = Field(
        sa_column=sa.Column(sa.Numeric(precision=4, scale=2), nullable=False)
    )
    width: condecimal(decimal_places=2) = Field(
        sa_column=sa.Column(sa.Numeric(precision=4, scale=2), nullable=False)
    )
    depth: condecimal(decimal_places=2) = Field(
        sa_column=sa.Column(sa.Numeric(precision=4, scale=2), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    trays: List["Tray"] = Relationship(back_populates="size_class")
    items: List["Item"] = Relationship(back_populates="size_class")
    non_tray_items: List["NonTrayItem"] = Relationship(back_populates="size_class")
    shelf_types: List["ShelfType"] = Relationship(back_populates="size_class")
    shelving_job_discrepancies: List["ShelvingJobDiscrepancy"] = Relationship(
        back_populates="size_class",
        sa_relationship_kwargs={
            "primaryjoin": "ShelvingJobDiscrepancy.size_class_id==SizeClass.id",
            "lazy": "selectin"
        }
    )
