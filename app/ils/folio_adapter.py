import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import httpx
from folioclient import (
    FolioAuthenticationError,
    FolioClient,
    FolioHTTPError,
    FolioTimeoutError,
)

from app.logger import inventory_logger
from app.ils import folio_client_cache
from app.ils.interfaces import (
    BaseILSAdapter,
    ILSCheckInResponse,
    ILSItemMetadata,
    ILSCheckInStatus,
    ILSRequestItem
)


class FolioILSAdapter(BaseILSAdapter):
    _BATCH_SIZE = 50
    _MAX_CONCURRENT_BATCHES = 3
    _AUTH_RETRY_ATTEMPTS = 3
    _AUTH_RETRY_BACKOFF_SECONDS = 1.0

    def _get_client(self) -> FolioClient:
        """
        Returns an authenticated FolioClient for this adapter's ILSConfiguration,
        reusing a cached client (module-level, keyed by ILSConfiguration.id) when one
        exists.
        """
        cached_client = folio_client_cache.get_client(self.config_id) if self.config_id else None
        if cached_client:
            return cached_client

        try:
            client = FolioClient(
                self.base_url,
                self.tenant_id,
                self.auth_client_id,
                self.auth_client_secret,
            )
        except Exception as e:
            inventory_logger.error(f"Folio Login Failed for Tenant {self.tenant_id}: {str(e)}")
            raise

        if self.config_id:
            folio_client_cache.set_client(self.config_id, client)

        return client

    def validate_item(self, barcode_value: str) -> bool:
        """
        Checks if an item physically exists in FOLIO inventory.
        """
        try:
            client = self._get_client()
            items = client.folio_get(
                "/inventory/items",
                key="items",
                query_params={"query": f'(barcode=="{barcode_value}")'},
            )
            return bool(items)

        except Exception as e:
            inventory_logger.error(f"FOLIO Adapter validate_item error: {str(e)}")
            return False

    def validate_items_batch(self, barcodes: List[str]) -> Dict[str, bool]:
        # Initialize each barcode as "not processed" (False)
        results: Dict[str, bool] = {}
        for barcode in barcodes:
            results[barcode] = False# Initialize each barcode as "not processed" (False)

        batches = []
        # Split the barcodes list into chunks of size _BATCH_SIZE
        for i in range(0, len(barcodes), self._BATCH_SIZE):
            batch = barcodes[i:i + self._BATCH_SIZE]
            batches.append(batch)

        with ThreadPoolExecutor(max_workers=self._MAX_CONCURRENT_BATCHES) as executor:
            future_to_batch = {
                executor.submit(self._lookup_batch, batch): batch for batch in batches
            }
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    found_barcodes = future.result()
                except Exception as e:
                    inventory_logger.error(
                        f"FOLIO Adapter validate_items_batch giving up on batch "
                        f"(barcodes={batch}): {str(e)}"
                    )
                    continue  # left as False (fail closed) from the initial dict

                for barcode in batch:
                    results[barcode] = barcode in found_barcodes

        return results

    def _lookup_batch(self, barcodes: List[str]) -> set:
        query = " or ".join(f'barcode=="{barcode}"' for barcode in barcodes)

        attempt = 0
        while True:
            attempt += 1
            try:
                client = self._get_client()
                items = client.folio_get(
                    "/inventory/items",
                    key="items",
                    query_params={"query": f"({query})", "limit": len(barcodes)},
                )
                return {item.get("barcode") for item in (items or [])}

            except (FolioAuthenticationError, FolioTimeoutError, httpx.TimeoutException) as e:
                if attempt >= self._AUTH_RETRY_ATTEMPTS:
                    inventory_logger.error(
                        f"FOLIO Adapter batch lookup authentication timeout, giving "
                        f"up after {attempt} attempt(s): {str(e)}"
                    )
                    raise

                inventory_logger.warning(
                    f"FOLIO Adapter batch lookup authentication timeout on attempt "
                    f"{attempt}, retrying: {str(e)}"
                )
                if self.config_id:
                    folio_client_cache.clear_client(self.config_id)
                time.sleep(self._AUTH_RETRY_BACKOFF_SECONDS * attempt)

    def check_in_item(self, barcode_value: str, service_point_override: Optional[str] = None) -> ILSCheckInResponse:
        """
        Performs a check-in action against FOLIO circulation API.
        We attempt to read the raw status from the response.
        """
        try:
            client = self._get_client()

            # FOLIO check-in requires a service point.
            payload = {
                "itemBarcode": barcode_value,
                "servicePointId": service_point_override or self.ils_service_point_id or "00000000-0000-0000-0000-000000000000",
                "checkInDate": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }

            data = client.folio_post("/circulation/check-in-by-barcode", payload) or {}

            # FOLIO returns item status inside item object of the response
            item = data.get("item", {})
            status_obj = item.get("status", {})
            raw_status = status_obj.get("name", "Available")

            return ILSCheckInResponse(
                success=True,
                status=ILSCheckInStatus.AVAILABLE if raw_status == "Available" else ILSCheckInStatus.UNKNOWN,
                raw_status_string=raw_status,
            )

        except FolioHTTPError as e:
            # e.message defaults to the raw response body; prefer FOLIO's structured
            # error message when the body is JSON with an "errors" array.
            error_msg = e.message
            try:
                err_json = e.response.json()
                if "errors" in err_json and len(err_json["errors"]) > 0:
                    error_msg = err_json["errors"][0].get("message", error_msg)
            except Exception:
                pass

            inventory_logger.error(f"FOLIO Adapter check_in_item error: {error_msg}")
            return ILSCheckInResponse(
                success=False,
                status=ILSCheckInStatus.SYNC_ERROR,
                raw_status_string="",
                error_message=f"FOLIO Check-in failed: {error_msg}"
            )

        except Exception as e:
            inventory_logger.error(f"FOLIO Adapter check_in_item error: {str(e)}")
            return ILSCheckInResponse(
                success=False,
                status=ILSCheckInStatus.SYNC_ERROR,
                raw_status_string="",
                error_message=str(e)
            )

    def fetch_item_metadata(self, barcode_value: str) -> Optional[ILSItemMetadata]:
        """
        Dynamically fetches live data from FOLIO Inventory without saving it to FETCH2.
        """
        try:
            client = self._get_client()
            items = client.folio_get(
                "/inventory/items",
                key="items",
                query_params={"query": f'(barcode=="{barcode_value}")'},
            )
            if not items:
                return None

            item = items[0]

            # FOLIO item structures can be deep, doing a best effort extraction
            title = item.get("title", 'Unknown Title')
            call_number = item.get("itemLevelCallNumber") or item.get("callNumber")
            material_type = item.get("materialType", {}).get("name")

            # Author usually comes from instance relationship or contributors
            author = None
            if item.get("contributorNames"):
                author = item["contributorNames"][0].get("name")

            return ILSItemMetadata(
                title=title,
                author=author,
                call_number=call_number,
                material_type=material_type,
                is_valid_location=True
            )
        except Exception as e:
            inventory_logger.error(f"FOLIO Adapter fetch_item_metadata error: {str(e)}")
            return None

    def fetch_pending_requests(self) -> List[ILSRequestItem]:
        """
        Polls FOLIO for any open, unfulfilled page requests that need fulfillment.
        """
        try:
            client = self._get_client()
            # Poll for Requests that are open pages targeted at our service point
            query = '(status=="Open - Not yet filled" and requestType=="Page")'
            if self.ils_service_point_id:
                query += f' and pickupServicePointId=="{self.ils_service_point_id}"'

            requests = client.folio_get(
                "/circulation/requests",
                key="requests",
                query_params={"query": query, "limit": 50},
            )

            requests_list = []
            for req in requests or []:
                item_obj = req.get("item", {})
                requests_list.append(ILSRequestItem(
                    request_id=req.get("id"),
                    item_barcode=item_obj.get("barcode", ""),
                    patron_id=req.get("requesterId", "Unknown"),
                    destination=req.get("pickupServicePointId", "Default Location")
                ))

            return requests_list
        except Exception as e:
            inventory_logger.error(f"FOLIO Adapter fetch_pending_requests error: {str(e)}")
            return []
