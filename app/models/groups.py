import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship

from app.models.user_groups import UserGroup
from app.models.group_permissions import GroupPermission


class Group(SQLModel, table=True):
    """
    Class to represent user Groups.

    - Groups have permissions
    - UserGroup join:
        - One Group has many users
        - Each User can belong to many groups
    """

    __tablename__ = "groups"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.SmallInteger, default=None)
    name: str = Field(max_length=75, sa_column=sa.VARCHAR, nullable=False, unique=True)
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    users: List["User"] = Relationship(back_populates="groups", link_model=UserGroup)
    permissions: List["Permission"] = Relationship(
        back_populates="groups", link_model=GroupPermission
    )
