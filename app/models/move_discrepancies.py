# /code/app/models/move_discrepancies.py - ULTIMATE, UNBREAKABLE FIX FOR FK RESOLUTION

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Integer, VARCHAR, ForeignKey, String, CheckConstraint

from typing import Optional
from datetime import datetime, timezone
from app.database.base import Base 

# Dependencies (MUST BE IMPORTED FOR ABSOLUTE FK REFERENCE)
from app.models.container_types import ContainerType
from app.models.owners import Owner
from app.models.size_class import SizeClass


class MoveDiscrepancy(Base): 
    
    __tablename__ = "move_discrepancies"
    __table_args__ = (
        CheckConstraint(
            "(tray_id IS NOT NULL) OR (non_tray_item_id IS NOT NULL) OR (item_id IS NOT NULL)",
            name="ck_s_discrepancy_tray_item_xor_non_tray",
        ),
    )

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Foreign Keys (CRITICAL FIX: Absolute Foreign Keys)
    tray_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trays.id"), nullable=True)
    item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("items.id"), nullable=True)
    non_tray_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("non_tray_items.id"), nullable=True)
    
    # CRITICAL FIXES: ABSOLUTE FOREIGN KEY REFERENCES
    container_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ContainerType.__table__.c.id), nullable=True)
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Owner.__table__.c.id), nullable=True)
    size_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey(SizeClass.__table__.c.id), nullable=True)


    # Location Fields
    original_assigned_location: Mapped[Optional[str]] = mapped_column(String(175), nullable=True)
    current_assigned_location: Mapped[Optional[str]] = mapped_column(String(175), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(350), nullable=True)
    
    # --- RELATIONSHIPS ---
    tray: Mapped[Optional["Tray"]] = relationship(back_populates="move_discrepancies")
    item: Mapped[Optional["Item"]] = relationship(back_populates="move_discrepancies")
    non_tray_item: Mapped[Optional["NonTrayItem"]] = relationship(back_populates="move_discrepancies")
    
    # CRITICAL FIX: Explicitly link forward relations
    container_type: Mapped[Optional[ContainerType]] = relationship(
        back_populates="move_discrepancies",
        foreign_keys=[container_type_id]
    )
    assigned_user: Mapped[Optional["User"]] = relationship(back_populates="move_discrepancies")
    owner: Mapped[Optional[Owner]] = relationship(back_populates="move_discrepancies")
    size_class: Mapped[Optional[SizeClass]] = relationship(back_populates="move_discrepancies")