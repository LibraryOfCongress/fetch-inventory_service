# /app/models/shelving_job_discrepancies.py - ULTIMATE, UNBREAKABLE FIX FOR FK RESOLUTION

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Integer, VARCHAR, ForeignKey, String, CheckConstraint

from typing import Optional, List
from datetime import datetime, timezone
from app.database.base import Base 

# Dependencies (MUST BE IMPORTED FOR ABSOLUTE FK REFERENCE)
from app.models.shelving_jobs import ShelvingJob # <--- CRITICAL IMPORT
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.owners import Owner
from app.models.size_class import SizeClass


class ShelvingJobDiscrepancy(Base): 
    __tablename__ = "shelving_job_discrepancies"
    

    __table_args__ = (
        sa.CheckConstraint(
            "(tray_id IS NOT NULL) OR (non_tray_item_id IS NOT NULL)",
            name="ck_s_discrepancy_tray_xor_non_tray",
        ),
    )

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Foreign Keys
    # CRITICAL FIX: Use ShelvingJob.__table__.c.id for explicit, unbreakable reference
    shelving_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ShelvingJob.__table__.c.id), nullable=True)

    # Standard FKs (less likely to be circular)
    tray_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trays.id"), nullable=True)
    non_tray_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("non_tray_items.id"), nullable=True)
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # CRITICAL FIXES: ABSOLUTE FOREIGN KEY REFERENCES
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Owner.__table__.c.id), nullable=True)
    size_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey(SizeClass.__table__.c.id), nullable=True)


    # Location Fields
    assigned_location: Mapped[Optional[str]] = mapped_column(String(175), nullable=True)
    pre_assigned_location: Mapped[Optional[str]] = mapped_column(String(175), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(350), nullable=True)
    
    # --- RELATIONSHIPS ---
    
    # The relationship is fixed by using primaryjoin to link to the FK
    shelving_job: Mapped[Optional["ShelvingJob"]] = relationship(
        back_populates="shelving_job_discrepancies",
        primaryjoin="ShelvingJobDiscrepancy.shelving_job_id==ShelvingJob.id"
    )
    
    # Standard relationships using string forward references
    tray: Mapped[Optional["Tray"]] = relationship(back_populates="shelving_job_discrepancies")
    non_tray_item: Mapped[Optional["NonTrayItem"]] = relationship(back_populates="shelving_job_discrepancies")
    assigned_user: Mapped[Optional["User"]] = relationship(back_populates="shelving_job_discrepancies")
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="shelving_job_discrepancies")
    size_class: Mapped[Optional["SizeClass"]] = relationship(back_populates="shelving_job_discrepancies")