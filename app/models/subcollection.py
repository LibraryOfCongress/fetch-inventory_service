import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
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

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    name: str = Field(sa_column=sa.Column(sa.VARCHAR(50), nullable=False, unique=True))
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    items: List[Item] = Relationship(back_populates="subcollection")
    non_tray_items: List[NonTrayItem] = Relationship(back_populates="subcollection")
