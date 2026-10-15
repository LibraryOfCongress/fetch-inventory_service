from typing import List, Optional
from app.ils.interfaces import (
    BaseILSAdapter,
    ILSCheckInResponse,
    ILSItemMetadata,
    ILSRequestItem,
    ILSCheckInStatus
)

class MockILSAdapter(BaseILSAdapter):
    """
    Mock adapter that fakes responses so UI developers and system workflows
    can be tested without a real external connection blocking development.
    """

    def validate_item(self, barcode: str) -> bool:
        # Mock logic: any barcode starting with 'FAIL' is considered a failure
        if barcode.startswith("FAIL"):
            return False
        return True

    def fetch_item_metadata(self, barcode: str) -> ILSItemMetadata:
        if barcode.startswith("FAIL"):
             return ILSItemMetadata(
                title="Unknown Item",
                author=None,
                call_number=None,
                material_type=None,
                is_valid_location=False
            )
            
        return ILSItemMetadata(
            title=f"Mock Title for {barcode}",
            author="Test Author",
            call_number=f"QC.123.{barcode[-3:]}",
            material_type="Book",
            is_valid_location=True
        )

    def check_in_item(self, barcode: str, service_point_override: Optional[str] = None) -> ILSCheckInResponse:
        if barcode.startswith("FAIL"):
             return ILSCheckInResponse(
                success=False,
                status=ILSCheckInStatus.MISSING,
                raw_status_string="Not Found",
                error_message="Item barcode not found in mock database."
             )
             
        if barcode.startswith("HOLD"):
             return ILSCheckInResponse(
                success=True,
                status=ILSCheckInStatus.ON_HOLD,
                raw_status_string="On hold shelf",
                error_message="Item successfully checked in but is flagged for a hold request."
             )
             
        # Normal success
        # MOCK SIMULATION NOTE: since this is a mocked endpoint without a real request payload context 
        # (PickList vs Shelving), we just return a static success state. The calling FETCH system will
        # compare it against its expected config based on the hook context. We will simulate returning the exact
        # expected_shelved_status string here to make shelving tests pass by default.
        return ILSCheckInResponse(
            success=True,
            status=ILSCheckInStatus.AVAILABLE,
            raw_status_string=self.expected_shelved_status, # Use the dynamic config string to simulate a perfect match!
            error_message=None
        )

    def fetch_pending_requests(self) -> List[ILSRequestItem]:
        # Return two mock requests
        return [
            ILSRequestItem(
                request_id="REQ-1001",
                item_barcode="MOCK-111222",
                patron_id="PTN-404",
                destination="Main Library Desk"
            ),
             ILSRequestItem(
                request_id="REQ-1002",
                item_barcode="MOCK-999888",
                patron_id="PTN-505",
                destination="Science Library Desk"
            )
        ]
