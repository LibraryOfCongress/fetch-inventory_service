import uuid
import sqlalchemy as sa
from enum import Enum
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

# from sqlalchemy.schema import UniqueConstraint


class NonTrayItemStatus(str, Enum):
    In = "In"
    Out = "Out"


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

    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    status: Optional[str] = Field(
        sa_column=sa.Column(
            sa.Enum(
                NonTrayItemStatus,
                name="non_tray_item_status",
                nullable=False,
            )
        ),
        default=NonTrayItemStatus.In,
    )
    barcode_id: uuid.UUID = Field(
        foreign_key="barcodes.id", nullable=False, default=None, unique=True
    )
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=True)
    size_class_id: Optional[int] = Field(foreign_key="size_class.id", nullable=True)
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id", nullable=True
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
    scanned_for_shelving: Optional[bool] = Field(
        sa_column=sa.Boolean, default=False, nullable=False
    )
    verification_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="verification_jobs.id"
    )
    shelving_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="shelving_jobs.id"
    )
    shelf_position_id: Optional[int] = Field(
        foreign_key="shelf_positions.id", nullable=True
    )
    shelf_position_proposed_id: Optional[int] = Field(
        sa_column=sa.Column(sa.Integer, nullable=True, unique=False)
    )
    accession_dt: Optional[datetime] = Field(
        sa_column=sa.DateTime, default=None, nullable=True
    )
    withdrawal_dt: Optional[datetime] = Field(
        sa_column=sa.DateTime, default=None, nullable=True
    )
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
    media_type: Optional["MediaType"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    size_class: Optional["SizeClass"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    container_type: Optional["ContainerType"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    owner: Optional["Owner"] = Relationship(sa_relationship_kwargs={"uselist": False})
    accession_job: Optional["AccessionJob"] = Relationship(
        back_populates="non_tray_items"
    )
    verification_job: Optional["VerificationJob"] = Relationship(
        back_populates="non_tray_items"
    )
    shelving_job: Optional["ShelvingJob"] = Relationship(
        back_populates="non_tray_items"
    )
    shelf_position: Optional["ShelfPosition"] = Relationship(
        back_populates="non_tray_item"
    )
    subcollection: Optional["Subcollection"] = Relationship(
        back_populates="non_tray_items"
    )
    requests: List["Request"] = Relationship(back_populates="non_tray_item")
