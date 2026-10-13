# /code/app/models/item_retrieval_events.py - REFACRORED TO SQLALCHEMY V2

from typing import Optional, List
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, Integer

# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class ItemRetrievalEvent(Base): # <--- Inherit from Base
    """
    Model to represent the ItemRetrievalEvents table
    """

    # NOTE: __tablename__ is handled by Base.
    __tablename__ = "items_retrieval_events"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id"), nullable=False)
    pick_list_id: Mapped[int] = mapped_column(ForeignKey("pick_lists.id"), nullable=False)
    
    # REMOVED: create_dt and update_dt are inherited from Base

    # --- RELATIONSHIPS ---
    item: Mapped[Optional["Item"]] = relationship(back_populates="items_retrieval_events")
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="items_retrieval_events")
    pick_list: Mapped[Optional["PickList"]] = relationship(back_populates="items_retrieval_events")