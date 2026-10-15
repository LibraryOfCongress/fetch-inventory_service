import uuid
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timezone

from app.models.ils_configurations import AdapterTypeEnum

class ILSConfigurationInput(BaseModel):
    name: str
    adapter_type: AdapterTypeEnum
    base_url: str
    tenant_id: str
    auth_client_id: str
    auth_client_secret: str
    auth_token_url: Optional[str] = None
    expected_shelved_status: str = "Available"
    expected_refile_status: str = "Available"
    is_active: bool = True
    enable_accession_hook: bool = False
    enable_shelving_hook: bool = False
    enable_refile_hook: bool = False
    enable_requests_hook: bool = False
    enable_jit_metadata_hook: bool = False

class ILSConfigurationUpdateInput(BaseModel):
    name: Optional[str] = None
    adapter_type: Optional[AdapterTypeEnum] = None
    base_url: Optional[str] = None
    tenant_id: Optional[str] = None
    auth_client_id: Optional[str] = None
    auth_client_secret: Optional[str] = None
    auth_token_url: Optional[str] = None
    expected_shelved_status: Optional[str] = None
    expected_refile_status: Optional[str] = None
    is_active: Optional[bool] = None
    enable_accession_hook: Optional[bool] = None
    enable_shelving_hook: Optional[bool] = None
    enable_refile_hook: Optional[bool] = None
    enable_requests_hook: Optional[bool] = None
    enable_jit_metadata_hook: Optional[bool] = None

class ILSConfigurationBaseOutput(BaseModel):
    id: uuid.UUID
    name: str
    adapter_type: AdapterTypeEnum
    base_url: str
    tenant_id: str
    auth_client_id: str
    # Omit auth_client_secret from output for security!
    auth_token_url: Optional[str] = None
    expected_shelved_status: str
    expected_refile_status: str
    is_active: bool
    enable_accession_hook: bool
    enable_shelving_hook: bool
    enable_refile_hook: bool
    enable_requests_hook: bool
    enable_jit_metadata_hook: bool

class ILSConfigurationListOutput(ILSConfigurationBaseOutput):
    pass

class ILSConfigurationDetailOutput(ILSConfigurationBaseOutput):
    create_dt: Optional[datetime] = None
    update_dt: Optional[datetime] = None
