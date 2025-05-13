import sqlalchemy as sa


from datetime import datetime, timezone
from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship
from app.models.group_permissions import GroupPermission


class Permission(SQLModel, table=True):
    """
    Model to represent the Permissions table.
    """

    __tablename__ = "permissions"

    id: Optional[int] = Field(sa_column=sa.Column(sa.Integer, primary_key=True), default=None)
    name: str = Field(sa_column=sa.Column(sa.VARCHAR(50), nullable=False, unique=True))
    description: str = Field(sa_column=sa.Column(sa.VARCHAR(255), nullable=True))
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    groups: List["Group"] = Relationship(
        back_populates="permissions", link_model=GroupPermission
    )
