import uuid
from typing import Optional, List, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean
from sqlalchemy.types import Enum as SQLEnum
import enum

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.owners import Owner
    from app.models.building_ils_service_points import BuildingILSServicePoint

class AdapterTypeEnum(str, enum.Enum):
    FOLIO = "FOLIO"
    ALMA = "ALMA"
    CUSTOM_MIDDLEWARE = "CUSTOM_MIDDLEWARE"

class ILSConfiguration(Base):
    __tablename__ = "ils_configurations"

    id: Mapped[uuid.UUID] = mapped_column(sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    adapter_type: Mapped[AdapterTypeEnum] = mapped_column(SQLEnum(AdapterTypeEnum, name="adapter_type_enum"), nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    auth_client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_client_secret: Mapped[str] = mapped_column(String(500), nullable=False)
    auth_token_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ils_service_point_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    expected_shelved_status: Mapped[str] = mapped_column(String(100), nullable=False, default="Available")
    expected_refile_status: Mapped[str] = mapped_column(String(100), nullable=False, default="Available")
    expected_picklist_status: Mapped[str] = mapped_column(String(100), nullable=False, default="In Transit")
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enable_accession_hook: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enable_shelving_hook: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enable_refile_hook: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enable_requests_hook: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enable_jit_metadata_hook: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enable_picklist_hook: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    owners: Mapped[List["Owner"]] = relationship(back_populates="ils_configuration")
    # Per-building service point overrides for this ILS integration. See
    # app.models.building_ils_service_points.
    building_service_points: Mapped[List["BuildingILSServicePoint"]] = relationship(
        back_populates="ils_configuration"
    )
