import sqlalchemy as sa
from sqlalchemy import Column, DateTime

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

from app.models.user_groups import UserGroup


class User(SQLModel, table=True):
    """
    Model to represent the Users table.

       id: Optional is declared only for Python's needs before a db object is
           created. This field cannot be null in the database.
    """

    __tablename__ = "users"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.Integer, default=None)
    first_name: str = Field(
        max_length=50, sa_column=sa.VARCHAR, nullable=False, unique=False
    )
    last_name: str = Field(
        max_length=50, sa_column=sa.VARCHAR, nullable=False, unique=False
    )
    email: str = Field(max_length=100, sa_column=sa.VARCHAR, nullable=True, unique=True)
    # never serialize this
    fetch_auth_token: str = Field(
        max_length=300, sa_column=sa.VARCHAR, nullable=True, unique=False
    )
    fetch_auth_expiration: datetime = Field(
        sa_column=sa.DateTime, nullable=True, default=None, unique=False
    )
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )

    @property
    def name(self) -> str:
            return f"{self.first_name} {self.last_name}"

    accession_jobs: List["AccessionJob"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "primaryjoin": "AccessionJob.user_id==User.id",
            "lazy": "selectin"
        }
    )

    shelving_jobs: List["ShelvingJob"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "primaryjoin": "ShelvingJob.user_id==User.id",
            "lazy": "selectin"
        }
    )

    verification_jobs: List["VerificationJob"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "primaryjoin": "VerificationJob.user_id==User.id",
            "lazy": "selectin"
        }
    )

    pick_lists: List["PickList"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "primaryjoin": "PickList.user_id==User.id",
            "lazy": "selectin"
        }
    )

    groups: List["Group"] = Relationship(
        back_populates="users",
        link_model=UserGroup
    )

    refile_jobs: List["RefileJob"] = Relationship(
        back_populates="assigned_user",
        sa_relationship_kwargs={
            "primaryjoin": "RefileJob.assigned_user_id==User.id",
            "lazy": "selectin"
        }
    )

    withdraw_jobs: List["WithdrawJob"] = Relationship(
        back_populates="assigned_user",
        sa_relationship_kwargs={
            "primaryjoin": "WithdrawJob.assigned_user_id==User.id",
            "lazy": "selectin"
        }
    )

    batch_uploads: List["BatchUpload"] = Relationship(back_populates="user")

    created_accession_jobs: List["AccessionJob"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={
            "primaryjoin": "AccessionJob.created_by_id==User.id",
            "lazy": "selectin"
        }
    )

    created_verification_jobs: List["VerificationJob"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={
            "primaryjoin": "VerificationJob.created_by_id==User.id",
            "lazy": "selectin"
        }
    )

    created_shelving_jobs: List["ShelvingJob"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={
            "primaryjoin": "ShelvingJob.created_by_id==User.id",
            "lazy": "selectin"
        }
    )

    created_pick_lists: List["PickList"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={
            "primaryjoin": "PickList.created_by_id==User.id",
            "lazy": "selectin"
        }
    )

    created_refile_jobs: List["RefileJob"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={
            "primaryjoin": "RefileJob.created_by_id==User.id",
            "lazy": "selectin"
        }
    )

    created_withdraw_jobs: List["WithdrawJob"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={
            "primaryjoin": "WithdrawJob.created_by_id==User.id",
            "lazy": "selectin"
        }
    )

    shelving_job_discrepancies: List["ShelvingJobDiscrepancy"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "primaryjoin": "ShelvingJobDiscrepancy.user_id==User.id",
            "lazy": "selectin"
        }
    )
