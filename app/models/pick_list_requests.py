import sqlalchemy as sa

from typing import Optional, List
from sqlmodel import SQLModel, Field
from sqlalchemy.schema import UniqueConstraint


class PickListRequest(SQLModel, table=True):
    """
    Join table for many-to-many requests <--> pick_lists
    """

    __tablename__ = "pick_list_requests"
    __table_args__ = (
        UniqueConstraint(
            "request_id", "pick_list_id", name="uq_request_id_pick_list_id"
        ),
    )

    id: Optional[int] = Field(primary_key=True, sa_column=sa.SmallInteger, default=None)
    request_id: Optional[int] = Field(foreign_key="requests.id", nullable=False)
    pick_list_id: Optional[int] = Field(foreign_key="pick_lists.id", nullable=False)
