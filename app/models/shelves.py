import uuid, importlib
import sqlalchemy as sa

from sqlalchemy.sql import func

from typing import Optional, List
from datetime import datetime, timezone
from pydantic import condecimal
from sqlmodel import SQLModel, Field, Relationship, Session, select
from sqlalchemy.schema import UniqueConstraint

from app.models.owners import Owner
from app.models.ladders import Ladder
from app.models.container_types import ContainerType
from app.models.shelf_numbers import ShelfNumber
from app.models.shelf_types import ShelfType
from app.database.session import session_manager


class Shelf(SQLModel, table=True):
    """
    Model to represent the shelves table.
    Shelves belong to Ladders. One ladder may have many shelves, which are
    ordered from bottom to top along the ladder.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "shelves"
    __table_args__ = (
        UniqueConstraint(
            "ladder_id", "shelf_number_id", name="uq_ladder_id_shelf_number_id"
        ),
        UniqueConstraint("barcode_id"),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.Integer, primary_key=True, default=None))
    available_space: int = Field(
        sa_column=sa.Column(sa.SmallInteger, default=0, nullable=False)
    )
    location: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(175), nullable=True, unique=True, default=None)
    )
    internal_location: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(200), nullable=True, unique=True, default=None)
    )
    barcode_id: uuid.UUID = Field(
        foreign_key="barcodes.id", nullable=True, default=None, unique=True
    )
    height: condecimal(decimal_places=2) = Field(
        sa_column=sa.Column(sa.Numeric(precision=4, scale=2), nullable=False)
    )
    width: condecimal(decimal_places=2) = Field(
        sa_column=sa.Column(sa.Numeric(precision=4, scale=2), nullable=False)
    )
    depth: condecimal(decimal_places=2) = Field(
        sa_column=sa.Column(sa.Numeric(precision=4, scale=2), nullable=False)
    )
    sort_priority: Optional[int] = Field(
        sa_column=sa.Column(sa.SmallInteger, nullable=True, default=None)
    )
    container_type_id: int = Field(foreign_key="container_types.id", nullable=False)
    shelf_number_id: int = Field(foreign_key="shelf_numbers.id", nullable=False)
    shelf_type_id: int = Field(foreign_key="shelf_types.id", nullable=False)
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=True)
    ladder_id: int = Field(foreign_key="ladders.id", nullable=False)
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    def calc_available_space(self, session: Optional[Session] = None) -> int:
        """
        The reason this isn't done in memory is because of N+1 select issues.
        You'll thank me later.
        """
        # This is called on-demand in events or legacy data migration
        # session compatible with both sqlmodel and sqlalchemy (run time usage vs legacy migration)
        ShelfPosition = importlib.import_module("app.models.shelf_positions").ShelfPosition
        # Check if session is valid
        if session is None or not session.is_active:
            with session_manager() as new_session:
                return self._calculate_space(new_session, ShelfPosition)
        else:
            return self._calculate_space(session, ShelfPosition)

    def _calculate_space(self, session, ShelfPosition):
        total_positions = session.execute(
            select(func.count(ShelfPosition.id)).where(ShelfPosition.shelf_id == self.id)
        ).scalar() or 0  

        occupied_positions = session.execute(
            select(func.count(ShelfPosition.id))
            .where(ShelfPosition.shelf_id == self.id)
            .where(
                sa.or_(
                    ShelfPosition.tray != None,
                    ShelfPosition.non_tray_item != None
                )
            )
        ).scalar() or 0  

        self.available_space = total_positions - occupied_positions
        return self.available_space

    ladder: Ladder = Relationship(back_populates="shelves")
    owner: Owner = Relationship(back_populates="shelves")
    barcode: Optional["Barcode"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    shelf_type: ShelfType = Relationship(back_populates="shelves")
    shelf_number: ShelfNumber = Relationship(back_populates="shelves")
    container_type: ContainerType = Relationship(back_populates="shelves")
    shelf_positions: List["ShelfPosition"] = Relationship(back_populates="shelf")

    def update_shelf_address(self, session: Optional[Session] = None) -> str:
        if session and not self.ladder:
            session.refresh(self)  # Refresh to load relationships if needed

        shelf_number = self.shelf_number.number
        ladder = self.ladder
        ladder_number = self.ladder.ladder_number.number
        side = self.ladder.side
        side_orientation = self.ladder.side.side_orientation.name
        aisle = self.ladder.side.aisle
        aisle_number = self.ladder.side.aisle.aisle_number.number
        module = self.ladder.side.aisle.module
        building = self.ladder.side.aisle.module.building

        self.location = (
            f"{building.name}-{module.module_number}-{aisle_number}-"
            f"{side_orientation[0]}-{ladder_number}-{shelf_number}"
        )

        self.internal_location = (
            f"{building.id}-{module.id}-{aisle.id}-{side.id}"
            f"-{ladder.id}-{self.id}"
        )
