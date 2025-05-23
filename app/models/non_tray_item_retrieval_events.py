from typing import Optional
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship
import sqlalchemy as sa



class NonTrayItemRetrievalEvent(SQLModel, table=True):
    """
    Model to represent the non_tray_items_retrieval_events table
    """

    __tablename__ = "non_tray_items_retrieval_events"

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    non_tray_item_id: Optional[int] = Field(
       foreign_key="non_tray_items.id", nullable=False, unique=False)
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=False, unique=False)
    pick_list_id: Optional[int] = Field(
        foreign_key="pick_lists.id", nullable=False, unique=False)
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    non_tray_item: Optional["NonTrayItem"] = Relationship(
        back_populates="non_tray_items_retrieval_events"
    )
    owner: Optional["Owner"] = Relationship(
        back_populates="non_tray_items_retrieval_events"
    )
    pick_list: Optional["PickList"] = Relationship(
        back_populates="non_tray_items_retrieval_events"
    )

