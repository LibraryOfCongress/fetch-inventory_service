import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Relationship

from app.models.owners import Owner
from app.models.trays import Tray
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.container_types import ContainerType
from app.models.media_types import MediaType


class AccessionJob(SQLModel, table=True):
    """
    Model to represent the Accession Jobs table.
    Accession Jobs are used for ingesting new items, trays, and
    non-trayed items into the database.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "accession_jobs"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    media_type_id: Optional[int] = Field(
        foreign_key="media_types.id", nullable=True
    )
    trayed: bool = Field(sa_column=sa.Boolean, default=True, nullable=False)
    status: str = Field(
        sa_column=sa.Column(
            sa.Enum(
                "Created",
                "Paused",
                "Running",
                "Cancelled",
                "Completed",
                "Verified",
                name="accession_status",
            )
        ),
        default="Created",
        nullable=False,
    )
    user_id: Optional[int] = Field(
        sa_column=sa.Column(sa.SmallInteger, nullable=True, unique=False)
    )
    run_time: Optional[timedelta] = Field(sa_column=sa.Interval, nullable=True)
    last_transition: Optional[datetime] = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=True
    )
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=True)
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id", nullable=True
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    container_type: ContainerType = Relationship(back_populates="accession_jobs")
    media_type: MediaType = Relationship(back_populates="accession_jobs")
    owner: Owner = Relationship(back_populates="accession_jobs")
    trays: List[Tray] = Relationship(back_populates="accession_job")
    items: List[Item] = Relationship(back_populates="accession_job")
    non_tray_items: List[NonTrayItem] = Relationship(back_populates="accession_job")
    verification_jobs: List["VerificationJob"] = Relationship(
        back_populates="accession_job"
    )

    # TODO add item_count (Returns a count of related items)
    # TODO add tray_count (Returns a count of related trays)
    # TODO determine if non_tray_count needed
    # TODO return the above ordered by (item.create_dt) (tray.create_dt)
    # TODO ^ all of that in the schema
