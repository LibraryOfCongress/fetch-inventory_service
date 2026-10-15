# /code/app/models/owner_delivery_locations.py

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.schema import UniqueConstraint

from typing import TYPE_CHECKING

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.owners import Owner
    from app.models.delivery_locations import DeliveryLocation


class OwnerDeliveryLocation(Base):
    """
    Junction table for many-to-many relationship between Owner and DeliveryLocation.
    Each owner can have multiple allowed delivery locations.
    """
    __tablename__ = "owner_delivery_locations"

    __table_args__ = (
        UniqueConstraint("owner_id", "delivery_location_id", name="uq_owner_delivery_location"),
    )

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign Keys
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id"), nullable=False)
    delivery_location_id: Mapped[int] = mapped_column(ForeignKey("delivery_locations.id"), nullable=False)

    # Relationships
    owner: Mapped["Owner"] = relationship(back_populates="owner_delivery_locations")
    delivery_location: Mapped["DeliveryLocation"] = relationship(back_populates="owner_delivery_locations")
