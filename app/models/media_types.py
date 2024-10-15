import sqlalchemy as sa
from sqlalchemy import Column, DateTime

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

from app.models.items import Item


class MediaType(SQLModel, table=True):
    """
    Model to represent the Media Type table.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "media_types"

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True))
    name: str = Field(max_length=25, sa_column=sa.VARCHAR, nullable=False, unique=True)
    accession_jobs: List["AccessionJob"] = Relationship(back_populates="media_type")
    verification_jobs: List["VerificationJob"] = Relationship(
        back_populates="media_type"
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )

    items: List[Item] = Relationship(back_populates="media_type")
