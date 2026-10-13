# /code/app/models/workflow.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class Workflow(Base): # <--- Inherit from Base
    """
    Model to represent a shared Workflow identification between
    Accession Jobs and Verification Jobs.
    """

    # NOTE: __tablename__ is handled by Base.
    __tablename__ = "workflow" # NOTE: Explicit override to match singular table name

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(Integer, primary_key=True)
    
    # REMOVED: create_dt and update_dt are inherited from Base

    # --- RELATIONSHIPS ---
    accession_job: Mapped[Optional["AccessionJob"]] = relationship(back_populates="workflow")
    verification_job: Mapped[Optional["VerificationJob"]] = relationship(
        back_populates="workflow"
    )
    verification_change: Mapped[Optional["VerificationChange"]] = relationship(
        back_populates="workflow"
    )