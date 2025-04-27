from enum import Enum

import sqlalchemy as sa
from sqlalchemy import Column, DateTime

from typing import Optional, List
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Relationship

from app.models.buildings import Building


class PickListStatus(str, Enum):
    Created = "Created"
    Paused = "Paused"
    Running = "Running"
    Completed = "Completed"


class PickList(SQLModel, table=True):
    """
    Model to represent PickList table

          id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "pick_lists"

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True))
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", nullable=True)
    created_by_id: Optional[int] = Field(foreign_key="users.id", nullable=True)
    status: str = Field(
        sa_column=sa.Column(
            sa.Enum(
                PickListStatus,
                nullable=False,
                name="pick_list_status",
            )
        ),
        default=PickListStatus.Created,
    )
    building_id: Optional[int] = Field(
        default=None, foreign_key="buildings.id", nullable=True
    )
    last_transition: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    run_time: Optional[timedelta] = Field(
        sa_column=sa.Interval, nullable=False, default=timedelta()
    )
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )

    user: Optional["User"] = Relationship(
        back_populates="pick_lists",
        sa_relationship_kwargs={
            "primaryjoin": "PickList.user_id==User.id",
            "lazy": "selectin"
        }
    )

    created_by: Optional["User"] = Relationship(
        back_populates="created_pick_lists",
        sa_relationship_kwargs={
            "primaryjoin": "PickList.created_by_id==User.id",
            "lazy": "selectin"
        }
    )

    building: Optional[Building] = Relationship(back_populates="pick_lists")
    requests: List["Request"] = Relationship(back_populates="pick_list")
    withdraw_jobs: List["WithdrawJob"] = Relationship(back_populates="pick_list")
