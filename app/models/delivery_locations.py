import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class DeliveryLocation(SQLModel, table=True):
    """
    Model represents delivery locations for requests.

          id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "delivery_locations"
    # __table_args__ = (
    # )

    id: Optional[int] = Field(sa_column=sa.Column(sa.Integer, primary_key=True))
    name: Optional[str] = Field(
        max_length=50,
        sa_column=sa.VARCHAR,
        nullable=True,
        unique=True,
        default=None
    )
    address:str = Field(
        max_length=250,
        sa_column=sa.VARCHAR,
        nullable=False,
        unique=False,
        default=None
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    requests: List["Request"] = Relationship(back_populates="delivery_location")
