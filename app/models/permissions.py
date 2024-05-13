import sqlalchemy as sa

from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship
from app.models.group_permissions import GroupPermission


class Permission(SQLModel, table=True):
    """
    Model to represent the Permissions table.
    """

    __tablename__ = "permissions"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.Integer, default=None)
    name: str = Field(max_length=50, sa_column=sa.VARCHAR, nullable=False, unique=True)
    description: str = Field(max_length=255, sa_column=sa.VARCHAR, nullable=True)
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    groups: List["Group"] = Relationship(
        back_populates="permissions", link_model=GroupPermission
    )
