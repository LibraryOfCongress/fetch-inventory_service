import uuid
import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

from app.models.items import Item
from app.models.shelving_jobs import ShelvingJobTrayAssociation

# from sqlalchemy.schema import UniqueConstraint


class Tray(SQLModel, table=True):
    """
    Model to represent the trays table.
        Trays can be assigned to shelf positions and contains Items.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "trays"
    # __table_args__ = (
    # )

    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    accession_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="accession_jobs.id"
    )
    verification_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="verification_jobs.id"
    )
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id", nullable=True
    )
    barcode_id: uuid.UUID = Field(
        foreign_key="barcodes.id", nullable=False, default=None
    )
    scanned_for_accession: bool = Field(sa_column=sa.Boolean, default=False, nullable=False)
    collection_accessioned: bool = Field(sa_column=sa.Boolean, default=False, nullable=False)
    size_class_id: int = Field(foreign_key="size_class.id", nullable=False)
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=True)
    media_type_id: Optional[int] = Field(foreign_key="media_types.id", nullable=True)
    shelf_position_id: Optional[int] = Field(
        foreign_key="shelf_positions.id", nullable=True
    )
    conveyance_bin_id: Optional[int] = Field(
        foreign_key="conveyance_bins.id",
        nullable=True
    )
    accession_dt: Optional[datetime] = Field(sa_column=sa.DateTime, default=None, nullable=True)
    shelved_dt: Optional[datetime] = Field(sa_column=sa.DateTime, default=None, nullable=True)
    withdrawal_dt: Optional[datetime] = Field(sa_column=sa.DateTime, default=None, nullable=True)
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    # derived item count
    # derived item out count

    barcode: Optional["Barcode"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    media_type: Optional["MediaType"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    owner: Optional["Owner"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    container_type: Optional["ContainerType"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    size_class: Optional["SizeClass"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    conveyance_bin: Optional["ConveyanceBin"] = Relationship(back_populates="trays")
    accession_job: Optional["AccessionJob"] = Relationship(back_populates="trays")
    verification_job: Optional["VerificationJob"] = Relationship(back_populates="trays")
    items: List[Item] = Relationship(back_populates="tray")
    shelving_jobs: List["ShelvingJob"] = Relationship(
        back_populates="trays", link_model=ShelvingJobTrayAssociation
    )
