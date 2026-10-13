import uuid
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.types import Enum as SQLEnum
import enum

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.users import User

class WorkflowActionEnum(str, enum.Enum):
    ACCESSION = "ACCESSION"
    SHELVING = "SHELVING"
    REFILE = "REFILE"
    REQUEST_SYNC = "REQUEST_SYNC"
    PICKLIST = "PICKLIST"

class ILSSyncStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"

class ILSSyncError(Base):
    __tablename__ = "ils_sync_errors"

    id: Mapped[uuid.UUID] = mapped_column(sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_barcode: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    workflow_action: Mapped[WorkflowActionEnum] = mapped_column(SQLEnum(WorkflowActionEnum, name="workflow_action_enum"), nullable=False)
    error_message: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[ILSSyncStatusEnum] = mapped_column(SQLEnum(ILSSyncStatusEnum, name="ils_sync_status_enum"), nullable=False, default=ILSSyncStatusEnum.ACTIVE)
    
    resolved_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    resolved_by_user: Mapped[Optional["User"]] = relationship(foreign_keys=[resolved_by_user_id])
