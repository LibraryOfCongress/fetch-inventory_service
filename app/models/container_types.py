import sqlalchemy as sa
from sqlalchemy import Column, DateTime

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class ContainerType(SQLModel, table=True):
    """
    Model to represent container types.

    Container Types have owners.
    Container Types are tracked on shelves for types a Shelf accepts.
    Container Types are tracked on trays for container type it is.
    Container Types are tracked on items and the value is inherited from the tray.

    Container Types are tracked on non-trays(non-trayed-items), and the value is not inherited.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "container_types"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.Integer, default=None)
    type: str = Field(max_length=25, sa_column=sa.VARCHAR, nullable=False, unique=True)
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )

    # shelves assigned this container type
    shelves: List["Shelf"] = Relationship(back_populates="container_type")
    # accession jobs for this container type
    accession_jobs: List["AccessionJob"] = Relationship(back_populates="container_type")
    verification_jobs: List["VerificationJob"] = Relationship(
        back_populates="container_type"
    )
