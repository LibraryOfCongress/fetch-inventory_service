import sqlalchemy as sa


from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship, Session
from sqlalchemy.schema import UniqueConstraint

from app.models.shelves import Shelf
from app.models.shelf_position_numbers import ShelfPositionNumber


class ShelfPosition(SQLModel, table=True):
    """
    Model to represent the shelf positions table.
    One shelf may have many shelf positions.
    Shelf positions numbering is unique within a given shelf.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "shelf_positions"
    __table_args__ = (
        UniqueConstraint(
            "shelf_id",
            "shelf_position_number_id",
            name="uq_shelf_id_shelf_position_number_id",
        ),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True))
    location: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(175), nullable=True, unique=True, default=None)
    )
    internal_location: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(200), nullable=True, unique=True, default=None)
    )
    shelf_position_number_id: int = Field(
        foreign_key="shelf_position_numbers.id", nullable=False
    )
    shelf_id: int = Field(foreign_key="shelves.id", nullable=False)
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    shelf_position_number: ShelfPositionNumber = Relationship(
        back_populates="shelf_positions"
    )
    shelf: Shelf = Relationship(back_populates="shelf_positions")
    tray: Optional["Tray"] = Relationship(
        sa_relationship_kwargs={"uselist": False}, back_populates="shelf_position"
    )
    non_tray_item: Optional["NonTrayItem"] = Relationship(
        sa_relationship_kwargs={"uselist": False}, back_populates="shelf_position"
    )

    def update_position_address(self, session: Optional[Session] = None) -> str:
        if session and not self.shelf:
            session.refresh(self)  # Refresh to load relationships if needed

        shelf_number = self.shelf.shelf_number.number
        ladder = self.shelf.ladder
        ladder_number = self.shelf.ladder.ladder_number.number
        side = self.shelf.ladder.side
        side_orientation = self.shelf.ladder.side.side_orientation.name
        aisle = self.shelf.ladder.side.aisle
        aisle_number = self.shelf.ladder.side.aisle.aisle_number.number
        module = self.shelf.ladder.side.aisle.module
        building = self.shelf.ladder.side.aisle.module.building

        self.location = (
            f"{building.name}-{module.module_number}-{aisle_number}-"
            f"{side_orientation[0]}-{ladder_number}-{shelf_number}-{self.shelf_position_number.number}"
        )

        self.internal_location = (
            f"{building.id}-{module.id}-{aisle.id}-{side.id}"
            f"-{ladder.id}-{self.shelf.id}-{self.id}"
        )
