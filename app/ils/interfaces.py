import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum


class ILSCheckInStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    IN_TRANSIT = "IN_TRANSIT"
    ON_HOLD = "ON_HOLD"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"
    SYNC_ERROR = "SYNC_ERROR"


class ILSCheckInResponse(BaseModel):
    success: bool
    status: ILSCheckInStatus
    raw_status_string: str  # The exact string the ILS returned (e.g., "Item in place")
    error_message: Optional[str] = None


class ILSItemMetadata(BaseModel):
    title: str
    author: Optional[str]
    call_number: Optional[str]
    material_type: Optional[str]
    is_valid_location: bool


class ILSRequestItem(BaseModel):
    request_id: str
    item_barcode: str
    patron_id: str
    destination: str


class BaseILSAdapter(ABC):
    """
    The Base Abstract class that all ILS integrations (FolioAdapter, AlmaAdapter, MockILSAdapter, etc.)
    must inherit from and implement.
    """
    
    def __init__(
        self, 
        base_url: str, 
        tenant_id: str, 
        auth_client_id: str, 
        auth_client_secret: str, 
        auth_token_url: Optional[str] = None,
        ils_service_point_id: Optional[str] = None,
        expected_shelved_status: str = "Available",
        expected_refile_status: str = "In Transit",
        expected_picklist_status: str = "In Transit",
        config_id: Optional[uuid.UUID] = None
    ):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.auth_client_id = auth_client_id
        self.auth_client_secret = auth_client_secret
        self.auth_token_url = auth_token_url
        self.ils_service_point_id = ils_service_point_id
        self.expected_shelved_status = expected_shelved_status
        self.expected_refile_status = expected_refile_status
        self.expected_picklist_status = expected_picklist_status
        # Identifies the owning ILSConfiguration row; used by adapters (e.g. Folio)
        # that need to key a module-level auth token cache.
        self.config_id = config_id

    @abstractmethod
    def validate_item(self, barcode: str) -> bool:
        """
        [ACCESSION WORKFLOW]
        Queries the ILS to confirm if an item barcode exists and is assigned
        to the correct storage location.
        Returns True if valid, False if invalid (triggers Sync Error).
        """
        pass

    def validate_items_batch(self, barcodes: List[str]) -> Dict[str, bool]:
        """
        Adapters for ILSs with a real multi-barcode query endpoint (e.g.
        FolioILSAdapter) should override this with actual
        batching/concurrency/retry.

        Returns a dict mapping every input barcode to True (found/valid) or False
        (not found, or invalid).
        """
        validated_barcodes = {}
        for barcode in barcodes:
            validated_barcodes[barcode] = self.validate_item(barcode)
    
        return validated_barcodes


    @abstractmethod
    def fetch_item_metadata(self, barcode: str) -> ILSItemMetadata:
        """
        [JIT METADATA LOOKUP]
        Queries the ILS for bibliographic details (Title, Author, Call Number).
        Used by the Item Detail UI for read-only, ephemeral display to staff.
        """
        pass

    @abstractmethod
    def check_in_item(self, barcode: str, service_point_override: Optional[str] = None) -> ILSCheckInResponse:
        """
        [SHELVING & REFILE WORKFLOWS]
        Instructs the ILS to check the item in.
        Must parse the ILS response into a standard ILSCheckInResponse so FETCH
        can determine if it was a Hard Failure, a Soft Failure (In Transit),
        or a clean Available success.

        `service_point_override`, when provided, must take precedence over the
        adapter's own `self.ils_service_point_id` (which is resolved from the
        Owner-level ILSConfiguration). This lets callers check items in against
        the physical building's service point for Owners whose items are
        distributed across multiple facilities.
        """
        pass

    @abstractmethod
    def fetch_pending_requests(self) -> List[ILSRequestItem]:
        """
        [REQUESTS WORKFLOW]
        Queries the ILS for all pending "Page" or "Hold" requests destined 
        for this storage facility. Transforms the ILS-specific response into 
        a standard list of ILSRequestItem objects for FETCH to ingest.
        """
        pass
