import uuid
import sqlalchemy as sa
from enum import Enum
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

# from sqlalchemy.schema import UniqueConstraint


class ItemStatus(str, Enum):
    In = "In"
    Out = "Out"


class Item(SQLModel, table=True):
    """
    Model to represent the Items table.
        Items can be assigned to Trays, and each have a barcode.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "items"
    # __table_args__ = (
    # )

    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    status: Optional[str] = Field(
        sa_column=sa.Column(
            sa.Enum(
                ItemStatus,
                name="item_status",
                nullable=False,
            )
        ),
        default=ItemStatus.In,
    )
    barcode_id: uuid.UUID = Field(
        foreign_key="barcodes.id", nullable=False, default=None, unique=True
    )
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=True)
    size_class_id: int = Field(foreign_key="size_class.id", nullable=True)
    tray_id: Optional[int] = Field(default=None, nullable=True, foreign_key="trays.id")
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id", nullable=True
    )
    title: str = Field(
        max_length=4000, sa_column=sa.VARCHAR, nullable=True, unique=False
    )
    volume: str = Field(
        max_length=15, sa_column=sa.VARCHAR, nullable=True, unique=False
    )
    condition: str = Field(
        max_length=30, sa_column=sa.VARCHAR, nullable=True, unique=False
    )
    arbitrary_data: str = Field(
        max_length=255, sa_column=sa.VARCHAR, nullable=True, unique=False
    )
    subcollection_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="subcollections.id"
    )
    accession_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="accession_jobs.id"
    )
    scanned_for_accession: Optional[bool] = Field(
        sa_column=sa.Boolean, default=False, nullable=False
    )
    scanned_for_verification: Optional[bool] = Field(
        sa_column=sa.Boolean, default=False, nullable=False
    )
    verification_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="verification_jobs.id"
    )
    accession_dt: datetime = Field(sa_column=sa.DateTime, default=None, nullable=True)
    withdrawal_dt: datetime = Field(sa_column=sa.DateTime, default=None, nullable=True)
    media_type_id: Optional[int] = Field(foreign_key="media_types.id", nullable=True)
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    barcode: Optional["Barcode"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    accession_job: Optional["AccessionJob"] = Relationship(back_populates="items")
    verification_job: Optional["VerificationJob"] = Relationship(back_populates="items")
    subcollection: Optional["Subcollection"] = Relationship(back_populates="items")
    tray: Optional["Tray"] = Relationship(back_populates="items")
    media_type: Optional["MediaType"] = Relationship(back_populates="items")
    size_class: Optional["SizeClass"] = Relationship(back_populates="items")
    owner: Optional["Owner"] = Relationship(back_populates="items")
    requests: List["Request"] = Relationship(back_populates="item")
