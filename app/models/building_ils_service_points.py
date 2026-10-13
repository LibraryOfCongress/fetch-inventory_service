# /app/models/building_ils_service_points.py

import uuid
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import UniqueConstraint

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.buildings import Building
    from app.models.ils_configurations import ILSConfiguration


class BuildingILSServicePoint(Base):
    """
    Junction table mapping a physical Building to the FOLIO service point it
    should check in against, scoped per ILSConfiguration.

    A single ILSConfiguration.ils_service_point_id is only a per-Owner
    default. When an Owner's items are shelved across multiple physical
    buildings (e.g. Fort Meade and Cabin Branch), or when an organization
    runs more than one ILS integration, that single default isn't enough —
    each (Building, ILSConfiguration) pair needs its own override.
    """
    __tablename__ = "building_ils_service_points"

    __table_args__ = (
        UniqueConstraint("building_id", "ils_configuration_id", name="uq_building_ils_configuration"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    ils_configuration_id: Mapped[uuid.UUID] = mapped_column(
        sa.dialects.postgresql.UUID(as_uuid=True), ForeignKey("ils_configurations.id"), nullable=False
    )

    # The FOLIO/ILS service point identifier this building should check in
    # against for the paired ILSConfiguration.
    ils_service_point_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # --- RELATIONSHIPS ---
    building: Mapped["Building"] = relationship(back_populates="ils_service_points")
    ils_configuration: Mapped["ILSConfiguration"] = relationship(back_populates="building_service_points")
