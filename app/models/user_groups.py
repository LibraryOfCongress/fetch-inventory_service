import sqlalchemy as sa

from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy.schema import UniqueConstraint


class UserGroup(SQLModel, table=True):
    """
    Join table for many-to-many groups <--> users
    """

    __tablename__ = "user_groups"
    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uq_user_id_group_id"),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True), default=None)
    user_id: Optional[int] = Field(foreign_key="users.id", nullable=False)
    group_id: Optional[int] = Field(foreign_key="groups.id", nullable=False)
