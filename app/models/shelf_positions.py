# /app/models/shelf_positions.py - REFACTORED: Removed ShelfPositionNumber lookup table dependency

from sqlalchemy.orm import Mapped, mapped_column, relationship, aliased
from sqlalchemy import Integer, SmallInteger, String, ForeignKey, cast, select, func
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from typing import Optional, TYPE_CHECKING

from app.database.base import Base

# --- CRITICAL: DEFER IMPORTS TO BREAK CIRCULARITY ---
if TYPE_CHECKING:
    from app.models.trays import Tray
    from app.models.non_tray_items import NonTrayItem
# -----------------------------------------------------

# --- ABSOLUTE FK IMPORTS ---
from app.models.shelves import Shelf


class ShelfPosition(Base):
    """
    Model to represent the shelf positions table.
    """
    __tablename__ = "shelf_positions"

    __table_args__ = (
        UniqueConstraint(
            "shelf_id",
            "position_number",
            name="uq_shelf_id_position_number",
        ),
    )

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Location Fields removed (now properties)

    # Direct integer column (replaces shelf_position_number_id FK)
    position_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Foreign Keys
    shelf_id: Mapped[int] = mapped_column(ForeignKey(Shelf.__table__.c.id), nullable=False)

    # --- RELATIONSHIPS ---
    shelf: Mapped["Shelf"] = relationship(back_populates="shelf_positions")

    # One-to-One Relationships (Uses string forward references)
    tray: Mapped[Optional["Tray"]] = relationship(
        back_populates="shelf_position",
        uselist=False
    )
    non_tray_item: Mapped[Optional["NonTrayItem"]] = relationship(
        back_populates="shelf_position",
        uselist=False
    )

    # --- CUSTOM METHOD ---
    @hybrid_property
    def location(self) -> str:
        shelf = self.shelf
        if not shelf: return "Unknown"
        ladder = shelf.ladder
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
            f"{side.side_orientation.name[0]}-{ladder.ladder_number}-{shelf.shelf_number}-{self.position_number}"
        )

    @location.expression
    def location(cls):
        from app.models.shelves import Shelf
        from app.models.ladders import Ladder
        from app.models.sides import Side
        from app.models.side_orientations import SideOrientation
        from app.models.aisles import Aisle
        from app.models.modules import Module
        from app.models.buildings import Building

        sp_alias = aliased(cls)
        return (
            select(
                func.concat(
                    Building.name, "-",
                    Module.module_number, "-",
                    Aisle.aisle_number, "-",
                    func.substr(cast(SideOrientation.name, String), 1, 1), "-",
                    Ladder.ladder_number, "-",
                    Shelf.shelf_number, "-",
                    sp_alias.position_number
                )
            )
            .select_from(sp_alias)
            .join(Shelf, sp_alias.shelf_id == Shelf.id)
            .join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(SideOrientation, Side.side_orientation_id == SideOrientation.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .join(Module, Aisle.module_id == Module.id)
            .join(Building, Module.building_id == Building.id)
            .where(sp_alias.id == cls.id)
            .scalar_subquery()
        )

    @hybrid_property
    def internal_location(self) -> str:
        shelf = self.shelf
        if not shelf: return "Unknown"
        ladder = shelf.ladder
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
            f"-{ladder.id}-{shelf.id}-{self.id}"
        )

    @internal_location.expression
    def internal_location(cls):
        from app.models.shelves import Shelf
        from app.models.ladders import Ladder
        from app.models.sides import Side
        from app.models.aisles import Aisle
        from app.models.modules import Module
        from app.models.buildings import Building

        sp_alias = aliased(cls)
        return (
            select(
                func.concat(
                    cast(Building.id, String), "-",
                    cast(Module.id, String), "-",
                    cast(Aisle.id, String), "-",
                    cast(Side.id, String), "-",
                    cast(Ladder.id, String), "-",
                    cast(Shelf.id, String), "-",
                    cast(sp_alias.id, String)
                )
            )
            .select_from(sp_alias)
            .join(Shelf, sp_alias.shelf_id == Shelf.id)
            .join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .join(Module, Aisle.module_id == Module.id)
            .join(Building, Module.building_id == Building.id)
            .where(sp_alias.id == cls.id)
            .scalar_subquery()
        )
