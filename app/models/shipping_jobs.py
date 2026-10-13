
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy import Integer, Boolean, Enum as SQLEnum, Interval, TIMESTAMP, ForeignKey, BigInteger
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone, timedelta

from app.database.base import Base
from app.models.users import User  # Runtime import - matches AccessionJob/ShelvingJob pattern

if TYPE_CHECKING:
    from app.models.shipping_bins import ShippingBin
    
class ShippingJobStatus(str, Enum):
    Created = "Created"
    Assigned = "Assigned"
    Paused = "Paused"
    Running = "Running"
    Completed = "Completed"

class ShippingJob(Base):
    """
    Model to represent the Shipping Jobs table.
    """
    __tablename__ = "shipping_jobs"

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Status (Enum)
    status: Mapped[str] = mapped_column(
        SQLEnum(
            ShippingJobStatus,
            name="shipping_status",
            nullable=False,
        ),
        default=ShippingJobStatus.Created,
    )

    # Timestamps
    completed_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Run Time Tracking
    run_time: Mapped[Optional[timedelta]] = mapped_column(Interval, nullable=True, default=timedelta())
    
    # Last Transition
    last_transition: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )

    # Foreign Keys
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Relationships
    assigned_user: Mapped[Optional["User"]] = relationship(
        "User",
        backref=backref("shipping_jobs", lazy="selectin"),
        foreign_keys=[assigned_user_id],
        lazy="selectin"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        backref=backref("created_shipping_jobs", lazy="selectin"),
        foreign_keys=[created_by_id],
        lazy="selectin"
    )

    bins: Mapped[List["ShippingBin"]] = relationship(
        back_populates="shipping_job",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

