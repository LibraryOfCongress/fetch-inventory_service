from typing import Optional, List
from datetime import datetime

import sqlalchemy as sa
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint


class ShelfType(SQLModel, table=True):
    __tablename__ = "shelf_types"
    __table_args__ = (
        UniqueConstraint(
            "type", "size_class_id", name="uq_type_size_class_shelf_type"
        ),
    )

    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    type: Optional[str] = Field(
        max_length=50,
        sa_column=sa.VARCHAR,
        nullable=True,
        unique=False,
        index=True,
        default=None
    )
    size_class_id: Optional[int] = Field(foreign_key="size_class.id", nullable=False)
    max_capacity: int = Field(
        sa_column=sa.Column(sa.SmallInteger, nullable=False, default=0)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.DateTime, default=datetime.utcnow), nullable=False
    )
    size_class: "SizeClass" = Relationship(back_populates="shelf_types")
    shelves: List["Shelf"] = Relationship(back_populates="shelf_type")
