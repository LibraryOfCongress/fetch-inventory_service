import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
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

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True), default=None)
    name: str = Field(sa_column=sa.Column(sa.VARCHAR(75), nullable=False, unique=True))
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    users: List["User"] = Relationship(back_populates="groups", link_model=UserGroup)
    permissions: List["Permission"] = Relationship(
        back_populates="groups", link_model=GroupPermission
    )
