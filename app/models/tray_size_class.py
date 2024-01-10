import sqlalchemy as sa

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class TraySizeClass(SQLModel, table=True):
    """
    Model to represent the Tray Size Class table.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "tray_size_class"

    id: Optional[int] = Field(
        sa_column=sa.Column(sa.SmallInteger, primary_key=True)
    )
    name: str = Field(max_length=25, sa_column=sa.VARCHAR, nullable=False, unique=True)
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
