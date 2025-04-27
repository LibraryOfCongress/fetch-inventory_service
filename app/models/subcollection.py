import sqlalchemy as sa
from sqlalchemy import Column, DateTime

from typing import Optional, List
from datetime import datetime
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from sqlmodel import SQLModel, Field, Relationship


class Subcollection(SQLModel, table=True):
    """
    Model to represent the Subcollections table.
        Items and Non-Trayed Items can belong to Subcollections

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "subcollections"
    # __table_args__ = (
    # )

    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    name: str = Field(max_length=50, sa_column=sa.VARCHAR, nullable=False, unique=True)
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )

    items: List[Item] = Relationship(back_populates="subcollection")
    non_tray_items: List[NonTrayItem] = Relationship(back_populates="subcollection")
