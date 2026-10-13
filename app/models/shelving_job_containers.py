# /app/models/shelving_job_containers.py - NEW MODEL FOR SHELVE BY LIST FEATURE

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, BigInteger, Boolean, String, ForeignKey, TIMESTAMP

from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

from app.database.base import Base


if TYPE_CHECKING:
    from app.models.shelving_jobs import ShelvingJob
    from app.models.trays import Tray
    from app.models.non_tray_items import NonTrayItem
    from app.models.items import Item
    from app.models.shelf_positions import ShelfPosition


class ShelvingJobContainerStatus:
    """Status values for ShelvingJobContainer."""
    PENDING = "Pending"        # Added to list, not yet assigned
    ASSIGNED = "Assigned"      # Pre-assigned to a shelf position
    UNASSIGNED = "Unassigned"  # Could not be pre-assigned (no matching positions)
    SHELVED = "Shelved"        # Successfully shelved
    ERROR = "Error"            # Error during shelving


class ShelvingJobContainer(Base):
    """
    Tracks explicit list of containers for a Shelve by List job.
    This table manages the association between shelving jobs and their containers,
    including pre-assignment tracking and override information.
    """
    __tablename__ = "shelving_job_containers"

    __table_args__ = (
        sa.CheckConstraint(
            "(tray_id IS NOT NULL) OR (non_tray_item_id IS NOT NULL) OR (item_id IS NOT NULL)",
            name="ck_shelving_job_container_tray_xor_non_tray_xor_item",
        ),
    )

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key to ShelvingJob (required)
    shelving_job_id: Mapped[int] = mapped_column(
        ForeignKey("shelving_jobs.id", ondelete="CASCADE"),
        nullable=False
    )

    # Container Foreign Keys (exactly one should be set)
    tray_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trays.id"),
        nullable=True
    )
    non_tray_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("non_tray_items.id"),
        nullable=True
    )
    item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("items.id"),
        nullable=True
    )

    # Destination Tray (for Item -> Tray moves)
    destination_tray_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trays.id"),
        nullable=True
    )

    # Pre-assignment tracking
    proposed_shelf_position_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shelf_positions.id"),
        nullable=True
    )
    position_reserved_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True
    )
    
    # Actual shelving result
    actual_shelf_position_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shelf_positions.id"),
        nullable=True
    )
    shelved_dt: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True
    )

    # Override tracking
    was_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ShelvingJobContainerStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- RELATIONSHIPS ---

    shelving_job: Mapped["ShelvingJob"] = relationship(
        back_populates="shelving_job_containers"
    )

    tray: Mapped[Optional["Tray"]] = relationship(
        foreign_keys=[tray_id],
        lazy="selectin"
    )

    non_tray_item: Mapped[Optional["NonTrayItem"]] = relationship(
        foreign_keys=[non_tray_item_id],
        lazy="selectin"
    )

    item: Mapped[Optional["Item"]] = relationship(
        foreign_keys=[item_id],
        lazy="selectin"
    )

    destination_tray: Mapped[Optional["Tray"]] = relationship(
        foreign_keys=[destination_tray_id],
        lazy="selectin"
    )

    proposed_shelf_position: Mapped[Optional["ShelfPosition"]] = relationship(
        foreign_keys=[proposed_shelf_position_id],
        lazy="selectin"
    )

    actual_shelf_position: Mapped[Optional["ShelfPosition"]] = relationship(
        foreign_keys=[actual_shelf_position_id],
        lazy="selectin"
    )
