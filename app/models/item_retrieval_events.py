from typing import Optional
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
import sqlalchemy as sa
from sqlalchemy import Column, DateTime


class ItemRetrievalEvent(SQLModel, table=True):
    """
    Model to represent the ItemRetrievalEvents table
    """

    __tablename__ = "items_retrieval_events"
    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    item_id: int = Field(foreign_key="items.id", nullable=False, unique=False)
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=False, unique=False)
    pick_list_id: Optional[int] = Field(
        foreign_key="pick_lists.id", nullable=False, unique=False)
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    item: Optional["Item"] = Relationship(back_populates="items_retrieval_events")
    owner: Optional["Owner"] = Relationship(back_populates="items_retrieval_events")
    pick_list: Optional["PickList"] = Relationship(back_populates="items_retrieval_events")
