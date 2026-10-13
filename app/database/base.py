# base.py

from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
from sqlalchemy import DateTime, func, String, Column

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy database models.
    Provides automatic table naming and audit columns.
    """

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        # Simple pluralization: Item -> items, User -> users, etc.
        # Check this logic against your existing DB table names!
        return cls.__name__.lower() + "s"

    # Common audit columns (Assuming your models have these)
    # NOTE: These are Column objects, as is standard practice for Base
    create_dt = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    update_dt = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)