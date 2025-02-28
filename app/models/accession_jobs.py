import sqlalchemy as sa

from typing import Optional, List
from enum import Enum
from datetime import datetime, timezone, timedelta
from sqlmodel import SQLModel, Field, Relationship


from app.models.users import User
from app.models.owners import Owner
from app.models.trays import Tray
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.container_types import ContainerType
from app.models.media_types import MediaType


class AccessionJobStatus(str, Enum):
    Created = "Created"
    Paused = "Paused"
    Running = "Running"
    Cancelled = "Cancelled"
    Completed = "Completed"
    Verified = "Verified"


class AccessionJob(SQLModel, table=True):
    """
    Model to represent the Accession Jobs table.
    Accession Jobs are used for ingesting new items, trays, and
    non-trayed items into the database.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "accession_jobs"

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    workflow_id: Optional[int] = Field(foreign_key="workflow.id", nullable=True)
    media_type_id: Optional[int] = Field(foreign_key="media_types.id", nullable=True)
    trayed: bool = Field(sa_column=sa.Column(sa.Boolean, default=True, nullable=False))
    status: str = Field(
        sa_column=sa.Column(
            sa.Enum(
                AccessionJobStatus,
                nullable=False,
                name="accession_status",
            )
        ),
        default=AccessionJobStatus.Created,
    )
    user_id: Optional[int] = Field(foreign_key="users.id", nullable=True)
    created_by_id: Optional[int] = Field(foreign_key="users.id", nullable=True)
    run_time: Optional[timedelta] = Field(
        sa_column=sa.Column(sa.Interval, nullable=False, default=timedelta())
    )
    last_transition: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    size_class_id: Optional[int] = Field(
        foreign_key="size_class.id", nullable=True, default=None
    )
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=True)
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id", nullable=True
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    container_type: Optional[ContainerType] = Relationship(
        back_populates="accession_jobs"
    )
    media_type: Optional[MediaType] = Relationship(back_populates="accession_jobs")
    size_class: Optional["SizeClass"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    user: Optional[User] = Relationship(
        back_populates="accession_jobs",
        sa_relationship_kwargs={
            "primaryjoin": "AccessionJob.user_id==User.id",
            "lazy": "selectin"
        }
    )
    created_by: Optional[User] = Relationship(
        back_populates="created_accession_jobs",
        sa_relationship_kwargs={
            "primaryjoin": "AccessionJob.created_by_id==User.id",
            "lazy": "selectin"
        }
    )
    owner: Optional[Owner] = Relationship(back_populates="accession_jobs")
    trays: List[Tray] = Relationship(back_populates="accession_job")
    items: List[Item] = Relationship(back_populates="accession_job")
    non_tray_items: List[NonTrayItem] = Relationship(back_populates="accession_job")
    verification_jobs: List["VerificationJob"] = Relationship(
        back_populates="accession_job"
    )
    workflow: Optional["Workflow"] = Relationship(back_populates="accession_job")
