import sqlalchemy as sa

from typing import Optional
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship


class MoveDiscrepancy(SQLModel, table=True):
    __tablename__ = "move_discrepancies"
    __table_args__ = (
        sa.CheckConstraint(
            "(tray_id IS NOT NULL) OR (non_tray_item_id IS NOT NULL) OR (item_id IS NOT NULL)",
            name="ck_s_discrepancy_tray_item_xor_non_tray",
        ),
    )

    id: Optional[int] = Field(
        sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None
    )
    tray_id: Optional[int] = Field(foreign_key="trays.id", nullable=True, unique=False)
    item_id: Optional[int] = Field(foreign_key="items.id", nullable=True, unique=False)
    non_tray_item_id: Optional[int] = Field(
        foreign_key="non_tray_items.id", nullable=True, unique=False
    )
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id", nullable=True, unique=False
    )
    assigned_user_id: Optional[int] = Field(
        foreign_key="users.id", nullable=True, unique=False
    )
    owner_id: Optional[int] = Field(
        foreign_key="owners.id", nullable=True, unique=False
    )
    size_class_id: Optional[int] = Field(
        foreign_key="size_class.id", nullable=True, unique=False
    )
    original_assigned_location: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(175), nullable=True, unique=False, default=None)
    )
    current_assigned_location: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(175), nullable=True, unique=False, default=None)
    )
    error: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(350), nullable=True, unique=False)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(
            sa.TIMESTAMP(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        )
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(
            sa.TIMESTAMP(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        )
    )

    tray: Optional["Tray"] = Relationship(back_populates="move_discrepancies")
    item: Optional["Item"] = Relationship(back_populates="move_discrepancies")
    non_tray_item: Optional["NonTrayItem"] = Relationship(
        back_populates="move_discrepancies"
    )
    container_type: Optional["ContainerType"] = Relationship(
        back_populates="move_discrepancies"
    )
    assigned_user: Optional["User"] = Relationship(
        back_populates="move_discrepancies"
    )
    owner: Optional["Owner"] = Relationship(back_populates="move_discrepancies")
    size_class: Optional["SizeClass"] = Relationship(
        back_populates="move_discrepancies"
    )
