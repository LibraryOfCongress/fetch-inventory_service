import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

from app.models.pick_lists import PickList


class Request(SQLModel, table=True):
    """
    Model represents the requests table, to handle external requests
    for retrieving items / non-trays from inventory.

          id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.

          table constraint - must have an item or a non-tray
    """

    __tablename__ = "requests"
    __table_args__ = (
        sa.CheckConstraint(
            "(item_id IS NULL AND non_tray_item_id IS NOT NULL) OR (non_tray_item_id IS NULL AND item_id IS NOT NULL)",
            name="ck_item_xor_non_tray",
        ),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True))
    request_type_id: Optional[int] = Field(
        default=None, nullable=True, unique=False, foreign_key="request_types.id"
    )
    item_id: Optional[int] = Field(
        default=None, nullable=True, unique=False, foreign_key="items.id"
    )
    non_tray_item_id: Optional[int] = Field(
        default=None, nullable=True, unique=False, foreign_key="non_tray_items.id"
    )
    building_id: int = Field(
        default=None, nullable=True, unique=False, foreign_key="buildings.id"
    )
    delivery_location_id: Optional[int] = Field(
        default=None, nullable=True, unique=False, foreign_key="delivery_locations.id"
    )
    priority_id: Optional[int] = Field(
        default=None, nullable=True, unique=False, foreign_key="priorities.id"
    )
    external_request_id: Optional[str] = Field(
        max_length=255, sa_column=sa.VARCHAR, nullable=True, unique=False, default=None
    )
    pick_list_id: Optional[int] = Field(
        default=None, nullable=True, unique=False, foreign_key="pick_lists.id"
    )
    batch_upload_id: Optional[int] = Field(
        default=None, nullable=True, unique=False, foreign_key="batch_uploads.id"
    )
    fulfilled: Optional[bool] = Field(
        sa_column=sa.Boolean, default=False, nullable=False
    )
    requestor_name: Optional[str] = Field(
        max_length=50, sa_column=sa.VARCHAR, nullable=True, unique=False, default=None
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    item: Optional["Item"] = Relationship(back_populates="requests")
    non_tray_item: Optional["NonTrayItem"] = Relationship(back_populates="requests")
    request_type: Optional["RequestType"] = Relationship(back_populates="requests")
    priority: Optional["Priority"] = Relationship(back_populates="requests")
    delivery_location: Optional["DeliveryLocation"] = Relationship(
        back_populates="requests"
    )
    building: Optional["Building"] = Relationship(back_populates="requests")
    pick_list: PickList = Relationship(back_populates="requests")
    batch_upload: Optional["BatchUpload"] = Relationship(back_populates="requests")
