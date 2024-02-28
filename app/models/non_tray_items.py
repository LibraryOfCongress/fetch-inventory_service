import uuid
import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
# from sqlalchemy.schema import UniqueConstraint


class NonTrayItem(SQLModel, table=True):
    """
    Model to represent the non_tray_items table.
        Non tray items have a barcode, and while they may be a container,
        we view these as a standalone entity and ignore their contents.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "non_tray_items"
    # __table_args__ = (
    # )

    id: Optional[int] = Field(
        primary_key=True,
        sa_column=sa.BigInteger,
        default=None
    )
    barcode_id: uuid.UUID = Field(
        foreign_key="barcodes.id",
        nullable=False,
        default=None
    )
    owner_id: Optional[int] = Field(
        foreign_key="owners.id",
        nullable=True
    )
    size_class_id: int = Field(
        foreign_key="size_class.id",
        nullable=True
    )
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id",
        nullable=True
    )
    subcollection_id: Optional[int] = Field(
        default=None,
        nullable=True,
        foreign_key="subcollections.id"
    )
    accession_job_id: Optional[int] = Field(
        default=None,
        nullable=True,
        foreign_key="accession_jobs.id"
    )
    verification_job_id: Optional[int] = Field(
        default=None,
        nullable=True,
        foreign_key="verification_jobs.id"
    )
    accession_dt: datetime = Field(
        sa_column=sa.DateTime, default=None, nullable=True
    )
    withdrawal_dt: datetime = Field(
        sa_column=sa.DateTime, default=None, nullable=True
    )
    media_type_id: Optional[int] = Field(
        foreign_key="media_types.id",
        nullable=True
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    barcode: Optional["Barcode"] = Relationship(sa_relationship_kwargs={"uselist": False})
    accession_job: Optional["AccessionJob"] = Relationship(back_populates="non_tray_items")
    verification_job: Optional["VerificationJob"] = Relationship(back_populates="non_tray_items")
    subcollection: Optional["Subcollection"] = Relationship(back_populates="non_tray_items")
