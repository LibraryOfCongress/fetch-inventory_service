import sqlalchemy as sa

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
    email: str = Field(
        max_length=100, sa_column=sa.VARCHAR, nullable=True, unique=True
    )
    # never serialize this
    fetch_auth_token: str = Field(
        max_length=300, sa_column=sa.VARCHAR, nullable=True, unique=False
    )
    fetch_auth_expiration: datetime = Field(
        sa_column=sa.DateTime, nullable=True, default=None, unique=False
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    accession_jobs: List["AccessionJob"] = Relationship(back_populates="user")
    shelving_jobs: List["ShelvingJob"] = Relationship(back_populates="user")
    verification_jobs: List["VerificationJob"] = Relationship(back_populates="user")
    pick_lists: List["PickList"] = Relationship(back_populates="user")
    groups: List["Group"] = Relationship(back_populates="users", link_model=UserGroup)
    refile_jobs: List["RefileJob"] = Relationship(back_populates="assigned_user")
    withdraw_jobs: List["WithdrawJob"] = Relationship(back_populates="assigned_user")
