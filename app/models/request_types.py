import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship


class RequestType(SQLModel, table=True):
    """
    Model represents the requests types table, tracks request types.

          id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "request_types"
    # __table_args__ = (
    # )

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True))
    type: str = Field(
        sa_column=sa.Column(sa.VARCHAR(50), nullable=False, unique=True, default=None)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    requests: List["Request"] = Relationship(back_populates="request_type")
