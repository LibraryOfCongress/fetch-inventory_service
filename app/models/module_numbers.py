import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class ModuleNumber(SQLModel, table=True):
    """
    Model to represent the Module Numbers table.
    Module Numbers are unique within the table, but may be re-used 
    by Modules which may be in different buildings from one another.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "module_numbers"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.SmallInteger, default=None)
    number: int = Field(sa_column=sa.Column(sa.SmallInteger, nullable=False, unique=True))
    update_dt: datetime = Field(
        sa_column=sa.DateTime,
        default=datetime.utcnow(),
        nullable=False
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime,
        default=datetime.utcnow(),
        nullable=False
    )

    modules: List['Module'] = Relationship(back_populates="module_number")
