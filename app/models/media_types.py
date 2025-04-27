import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
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
    name: str = Field(sa_column=sa.Column(sa.VARCHAR(25), nullable=False, unique=True))
    accession_jobs: List["AccessionJob"] = Relationship(back_populates="media_type")
    verification_jobs: List["VerificationJob"] = Relationship(
        back_populates="media_type"
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    items: List[Item] = Relationship(back_populates="media_type")
