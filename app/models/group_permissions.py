from typing import Optional

import sqlalchemy as sa
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field


class GroupPermission(SQLModel, table=True):
    """
    Class to represent Group Permissions.
    - many-to-many relationship between Groups and Permissions
    """

    __tablename__ = "group_permissions"
    __table_args__ = (
        UniqueConstraint("permission_id", "group_id", name="uq_permission_id_group_id"),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True), default=None)
    group_id: Optional[int] = Field(foreign_key="groups.id", nullable=False)
    permission_id: Optional[int] = Field(foreign_key="permissions.id", nullable=False)
