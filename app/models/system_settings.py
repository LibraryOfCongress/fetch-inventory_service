# /code/app/models/system_settings.py

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime
from typing import Optional
from datetime import datetime, timezone

from app.database.base import Base


class SystemSetting(Base):
    """
    Model to represent system-wide configuration settings.
    Stores key-value pairs for configurable system behavior.
    """
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    create_dt: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    update_dt: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
