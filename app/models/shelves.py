# /app/models/shelves.py - REFACTORED: Removed ShelfNumber lookup table dependency

import uuid
import importlib
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session, aliased
from sqlalchemy import Integer, SmallInteger, ForeignKey, Numeric, String, \
    select, func, or_, cast
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from typing import Optional, List

from pydantic import condecimal

from app.database.base import Base
from app.models.owners import Owner
from app.models.ladders import Ladder
from app.models.container_types import ContainerType
from app.models.shelf_types import ShelfType
from app.database.session import session_manager


class Shelf(Base):
    """
    Model to represent the shelves table.
    """
    # CRITICAL FIX: Override Base's faulty pluralization to match existing DB table name
    __tablename__ = "shelves"

    __table_args__ = (
        UniqueConstraint(
            "ladder_id", "shelf_number", name="uq_ladder_id_shelf_number"
        ),
        UniqueConstraint("barcode_id"),
        UniqueConstraint(
            "ladder_id",
            "sort_priority",
            name="uq_ladder_id_sort_priority"
        )
    )

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Simple Fields
    available_space: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    # Foreign Key (UUID)
    barcode_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("barcodes.id"), nullable=True, unique=True)

    # Numeric Fields
    height: Mapped[condecimal] = mapped_column(Numeric(precision=4, scale=2), nullable=False)
    width: Mapped[condecimal] = mapped_column(Numeric(precision=4, scale=2), nullable=False)
    depth: Mapped[condecimal] = mapped_column(Numeric(precision=4, scale=2), nullable=False)

    sort_priority: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True, default=None)

    # Direct integer column (replaces shelf_number_id FK)
    shelf_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Foreign Keys (Integer)
    container_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ContainerType.__table__.c.id), nullable=True)
    shelf_type_id: Mapped[int] = mapped_column(ForeignKey(ShelfType.__table__.c.id), nullable=False)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Owner.__table__.c.id), nullable=True)
    ladder_id: Mapped[int] = mapped_column(ForeignKey(Ladder.__table__.c.id), nullable=False)

    # --- RELATIONSHIPS ---
    ladder: Mapped[Ladder] = relationship(back_populates="shelves")
    owner: Mapped[Optional[Owner]] = relationship(back_populates="shelves")
    barcode: Mapped[Optional["Barcode"]] = relationship(uselist=False)
    shelf_type: Mapped[ShelfType] = relationship(back_populates="shelves")

    container_type: Mapped[Optional[ContainerType]] = relationship(
        back_populates="shelves",
        foreign_keys=[container_type_id]
    )

    shelf_positions: Mapped[List["ShelfPosition"]] = relationship(
        back_populates="shelf",
        cascade="all, delete-orphan"
    )

    # --- METHODS ---

    def calc_available_space(self, session: Optional[Session] = None) -> int:
        """
        Calculates available space. Avoids N+1 select issues.
        """
        # Dynamic import to avoid circular dependency at module level
        ShelfPosition = importlib.import_module("app.models.shelf_positions").ShelfPosition

        # Check if session is valid
        if session is None or not session.is_active:
            with session_manager() as new_session:
                return self._calculate_space(new_session, ShelfPosition)
        else:
            return self._calculate_space(session, ShelfPosition)

    def _calculate_space(self, session: Session, ShelfPosition):
        # Get total positions count
        total_positions_query = select(func.count(ShelfPosition.id)).where(ShelfPosition.shelf_id == self.id)
        total_positions = session.execute(total_positions_query).scalar() or 0

        # Get occupied positions count (where tray OR non_tray_item is present)
        occupied_positions_query = (
            select(func.count(ShelfPosition.id))
            .where(ShelfPosition.shelf_id == self.id)
            .where(
                or_(
                    ShelfPosition.tray != None,
                    ShelfPosition.non_tray_item != None
                )
            )
        )
        occupied_positions = session.execute(occupied_positions_query).scalar() or 0

        self.available_space = total_positions - occupied_positions
        return self.available_space

    @hybrid_property
    def location(self) -> str:
        ladder = self.ladder
        if not ladder: return "Unknown"
        side = ladder.side
        if not side: return "Unknown"
        aisle = side.aisle
        if not aisle: return "Unknown"
        module = aisle.module
        if not module: return "Unknown"
        building = module.building
        if not building: return "Unknown"

        return (
            f"{building.name}-{module.module_number}-{aisle.aisle_number}-"
            f"{side.side_orientation.name[0]}-{ladder.ladder_number}-{self.shelf_number}"
        )

    @location.expression
    def location(cls):
        from app.models.ladders import Ladder
        from app.models.sides import Side
        from app.models.side_orientations import SideOrientation
        from app.models.aisles import Aisle
        from app.models.modules import Module
        from app.models.buildings import Building

        s_alias = aliased(cls)
        return (
            select(
                func.concat(
                    Building.name, "-",
                    Module.module_number, "-",
                    Aisle.aisle_number, "-",
                    func.substr(cast(SideOrientation.name, String), 1, 1), "-",
                    Ladder.ladder_number, "-",
                    s_alias.shelf_number
                )
            )
            .select_from(s_alias)
            .join(Ladder, s_alias.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(SideOrientation, Side.side_orientation_id == SideOrientation.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .join(Module, Aisle.module_id == Module.id)
            .join(Building, Module.building_id == Building.id)
            .where(s_alias.id == cls.id)
            .scalar_subquery()
        )

    @hybrid_property
    def internal_location(self) -> str:
        ladder = self.ladder
        if not ladder: return "Unknown"
        side = ladder.side
        if not side: return "Unknown"
        aisle = side.aisle
        if not aisle: return "Unknown"
        module = aisle.module
        if not module: return "Unknown"
        building = module.building
        if not building: return "Unknown"

        return (
            f"{building.id}-{module.id}-{aisle.id}-{side.id}"
            f"-{ladder.id}-{self.id}"
        )

    @internal_location.expression
    def internal_location(cls):
        from app.models.ladders import Ladder
        from app.models.sides import Side
        from app.models.aisles import Aisle
        from app.models.modules import Module
        from app.models.buildings import Building

        s_alias = aliased(cls)
        return (
            select(
                func.concat(
                    cast(Building.id, String), "-",
                    cast(Module.id, String), "-",
                    cast(Aisle.id, String), "-",
                    cast(Side.id, String), "-",
                    cast(Ladder.id, String), "-",
                    cast(s_alias.id, String)
                )
            )
            .select_from(s_alias)
            .join(Ladder, s_alias.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .join(Module, Aisle.module_id == Module.id)
            .join(Building, Module.building_id == Building.id)
            .where(s_alias.id == cls.id)
            .scalar_subquery()
        )
