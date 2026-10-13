from app.models.ils_configurations import ILSConfiguration
from app.models.ils_configurations import AdapterTypeEnum
from app.ils.interfaces import BaseILSAdapter
from app.ils.mock_adapter import MockILSAdapter
from app.ils.folio_adapter import FolioILSAdapter

def get_ils_adapter(config: ILSConfiguration) -> BaseILSAdapter:
    """
    Adapter Factory. Instantiates and returns the correct ILS Adapter implementation 
    based on the adapter_type specified in the given ILSConfiguration.
    """
    if config.adapter_type == AdapterTypeEnum.CUSTOM_MIDDLEWARE:
             return MockILSAdapter(
            base_url=config.base_url,
            tenant_id=config.tenant_id,
            auth_client_id=config.auth_client_id,
            auth_client_secret=config.auth_client_secret,
            auth_token_url=config.auth_token_url,
            ils_service_point_id=config.ils_service_point_id,
            expected_shelved_status=config.expected_shelved_status,
            expected_refile_status=config.expected_refile_status,
            expected_picklist_status=config.expected_picklist_status,
            config_id=config.id
        )
        
    elif config.adapter_type == AdapterTypeEnum.FOLIO:
        # Folio Adapter authenticating against a standard Okapi gateway via
        # POST /authn/login-with-expiry (username/password, via folioclient),
        # auth_client_id/auth_client_secret hold the FOLIO username/password;
        return FolioILSAdapter(
            base_url=config.base_url,
            tenant_id=config.tenant_id,
            auth_client_id=config.auth_client_id,
            auth_client_secret=config.auth_client_secret,
            auth_token_url=config.auth_token_url,
            ils_service_point_id=config.ils_service_point_id,
            expected_shelved_status=config.expected_shelved_status,
            expected_refile_status=config.expected_refile_status,
            expected_picklist_status=config.expected_picklist_status,
            config_id=config.id
        )
        
    elif config.adapter_type == AdapterTypeEnum.ALMA:
         # For now, return the Mock
         return MockILSAdapter(
            base_url=config.base_url,
            tenant_id=config.tenant_id,
            auth_client_id=config.auth_client_id,
            auth_client_secret=config.auth_client_secret,
            auth_token_url=config.auth_token_url,
            ils_service_point_id=config.ils_service_point_id,
            expected_shelved_status=config.expected_shelved_status,
            expected_refile_status=config.expected_refile_status,
            expected_picklist_status=config.expected_picklist_status,
            config_id=config.id
        )
        
    raise ValueError(f"Unknown ILS Adapter type configured: {config.adapter_type}")
