"""Unit tests for app/ils/folio_adapter.py — pure logic, FolioClient is mocked out."""
import time
import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest
from folioclient import (
    FolioAuthenticationError,
    FolioHTTPError,
    FolioTimeoutError,
    FolioValidationError,
)

from app.ils import folio_client_cache
from app.ils.folio_adapter import FolioILSAdapter
from app.ils.interfaces import ILSCheckInStatus


def _adapter(**overrides):
    kwargs = dict(
        base_url="https://folio.example.org",
        tenant_id="tenant1",
        auth_client_id="folio-user",
        auth_client_secret="folio-pass",
        ils_service_point_id="sp-1",
        config_id=None,
    )
    kwargs.update(overrides)
    return FolioILSAdapter(**kwargs)


def _mock_client_class(mock_client):
    """A stand-in for the FolioClient class whose constructor returns the given
    mock client instance instead of performing a real login."""
    return MagicMock(return_value=mock_client)


def _http_error(exc_cls, *, status_code, body: bytes):
    """Builds a real folioclient HTTP exception (as folio_get/folio_post would
    raise) so error-handling paths can be exercised against real attribute shapes."""
    request = httpx.Request("POST", "https://folio.example.org/circulation/check-in-by-barcode")
    response = httpx.Response(status_code, request=request, content=body)
    return exc_cls(body.decode(), request=request, response=response)


def _auth_error():
    request = httpx.Request("GET", "https://folio.example.org/inventory/items")
    response = httpx.Response(401, request=request, content=b"token expired")
    return FolioAuthenticationError(request=request, response=response)


def _timeout_error():
    request = httpx.Request("GET", "https://folio.example.org/inventory/items")
    return FolioTimeoutError("timed out", request=request)


# --------------------------------------------------------------------------- #
# validate_item
# --------------------------------------------------------------------------- #
def test_validate_item_true_when_folio_returns_items():
    mock_client = MagicMock()
    mock_client.folio_get.return_value = [{"id": "1", "barcode": "ABC123"}]
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        assert _adapter().validate_item("ABC123") is True

    mock_client.folio_get.assert_called_once_with(
        "/inventory/items", key="items", query_params={"query": '(barcode=="ABC123")'}
    )


def test_validate_item_false_when_folio_returns_no_items():
    mock_client = MagicMock()
    mock_client.folio_get.return_value = []
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        assert _adapter().validate_item("NOPE") is False


def test_validate_item_false_on_folio_error():
    mock_client = MagicMock()
    mock_client.folio_get.side_effect = _http_error(FolioHTTPError, status_code=500, body=b"boom")
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        assert _adapter().validate_item("ABC123") is False


# --------------------------------------------------------------------------- #
# validate_items_batch — [OFFSITE STORAGE CONFIRMATION]
# --------------------------------------------------------------------------- #
def test_validate_items_batch_chunks_into_batches_of_50():
    barcodes = [f"B{i}" for i in range(60)]  # 2 batches: 50 + 10
    mock_client = MagicMock()
    mock_client.folio_get.return_value = []
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        results = _adapter().validate_items_batch(barcodes)

    assert mock_client.folio_get.call_count == 2
    assert len(results) == 60

    call_sizes = sorted(
        call.kwargs["query_params"]["query"].count('barcode=="')
        for call in mock_client.folio_get.call_args_list
    )
    assert call_sizes == [10, 50]

    limits = sorted(call.kwargs["query_params"]["limit"] for call in mock_client.folio_get.call_args_list)
    assert limits == [10, 50]


def test_validate_items_batch_marks_missing_barcodes_false():
    mock_client = MagicMock()
    mock_client.folio_get.return_value = [{"barcode": "FOUND1"}]
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        results = _adapter().validate_items_batch(["FOUND1", "MISSING1"])

    assert results == {"FOUND1": True, "MISSING1": False}


def test_validate_items_batch_query_includes_all_barcodes_in_batch():
    mock_client = MagicMock()
    mock_client.folio_get.return_value = []
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        _adapter().validate_items_batch(["ABC123", "XYZ789"])

    query = mock_client.folio_get.call_args.kwargs["query_params"]["query"]
    assert 'barcode=="ABC123"' in query
    assert 'barcode=="XYZ789"' in query
    assert " or " in query


def test_validate_items_batch_retries_on_auth_timeout_then_succeeds():
    mock_client = MagicMock()
    mock_client.folio_get.side_effect = [_auth_error(), [{"barcode": "ABC123"}]]
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)), \
         patch("app.ils.folio_adapter.time.sleep"):
        results = _adapter().validate_items_batch(["ABC123"])

    assert results == {"ABC123": True}
    assert mock_client.folio_get.call_count == 2


def test_validate_items_batch_retries_on_connection_timeout():
    mock_client = MagicMock()
    mock_client.folio_get.side_effect = [_timeout_error(), [{"barcode": "ABC123"}]]
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)), \
         patch("app.ils.folio_adapter.time.sleep"):
        results = _adapter().validate_items_batch(["ABC123"])

    assert results == {"ABC123": True}
    assert mock_client.folio_get.call_count == 2


def test_validate_items_batch_clears_cached_client_before_retry():
    config_id = uuid.uuid4()
    mock_client = MagicMock()
    mock_client.folio_get.side_effect = [_auth_error(), [{"barcode": "ABC123"}]]

    try:
        with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)), \
             patch("app.ils.folio_adapter.time.sleep"), \
             patch("app.ils.folio_client_cache.clear_client") as mock_clear:
            _adapter(config_id=config_id).validate_items_batch(["ABC123"])

        mock_clear.assert_called_once_with(config_id)
    finally:
        folio_client_cache.clear_client(config_id)


def test_validate_items_batch_gives_up_after_max_auth_retries():
    mock_client = MagicMock()
    mock_client.folio_get.side_effect = _auth_error()  # every attempt fails
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)), \
         patch("app.ils.folio_adapter.time.sleep"):
        results = _adapter().validate_items_batch(["ABC123", "XYZ789"])

    # Fails closed: barcodes in an unrecoverable batch are reported as not found.
    assert results == {"ABC123": False, "XYZ789": False}
    assert mock_client.folio_get.call_count == FolioILSAdapter._AUTH_RETRY_ATTEMPTS


def test_validate_items_batch_does_not_retry_non_auth_errors():
    mock_client = MagicMock()
    mock_client.folio_get.side_effect = RuntimeError("boom")
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        results = _adapter().validate_items_batch(["ABC123"])

    assert results == {"ABC123": False}
    mock_client.folio_get.assert_called_once()


def test_validate_items_batch_caps_concurrent_batches_at_3():
    import threading

    lock = threading.Lock()
    state = {"current": 0, "max_seen": 0}

    def slow_lookup(*args, **kwargs):
        with lock:
            state["current"] += 1
            state["max_seen"] = max(state["max_seen"], state["current"])
        time.sleep(0.05)
        with lock:
            state["current"] -= 1
        barcode = kwargs["query_params"]["query"].split('"')[1]
        return [{"barcode": barcode}]

    mock_client = MagicMock()
    mock_client.folio_get.side_effect = slow_lookup

    # 6 batches of 1 barcode each (well under the 50-per-batch size) so each batch
    # maps to exactly one call, letting us count in-flight calls directly.
    barcodes = [f"B{i}" for i in range(6)]
    adapter = _adapter()
    adapter._BATCH_SIZE = 1

    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        adapter.validate_items_batch(barcodes)

    assert state["max_seen"] <= FolioILSAdapter._MAX_CONCURRENT_BATCHES


# --------------------------------------------------------------------------- #
# fetch_item_metadata
# --------------------------------------------------------------------------- #
def test_fetch_item_metadata_returns_none_when_not_found():
    mock_client = MagicMock()
    mock_client.folio_get.return_value = []
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        assert _adapter().fetch_item_metadata("NOPE") is None


def test_fetch_item_metadata_extracts_fields():
    mock_client = MagicMock()
    mock_client.folio_get.return_value = [{
        "title": "Moby Dick",
        "itemLevelCallNumber": "PS2384",
        "materialType": {"name": "Book"},
        "contributorNames": [{"name": "Herman Melville"}],
    }]
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        md = _adapter().fetch_item_metadata("ABC123")

    assert md.title == "Moby Dick"
    assert md.author == "Herman Melville"
    assert md.call_number == "PS2384"
    assert md.material_type == "Book"
    assert md.is_valid_location is True


def test_fetch_item_metadata_none_on_error():
    mock_client = MagicMock()
    mock_client.folio_get.side_effect = RuntimeError("network blip")
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        assert _adapter().fetch_item_metadata("ABC123") is None


# --------------------------------------------------------------------------- #
# check_in_item
# --------------------------------------------------------------------------- #
def test_check_in_item_success_available():
    mock_client = MagicMock()
    mock_client.folio_post.return_value = {"item": {"status": {"name": "Available"}}}
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        resp = _adapter().check_in_item("ABC123")

    assert resp.success is True
    assert resp.status is ILSCheckInStatus.AVAILABLE
    assert resp.raw_status_string == "Available"

    payload = mock_client.folio_post.call_args.args[1]
    assert payload["itemBarcode"] == "ABC123"
    assert payload["servicePointId"] == "sp-1"


def test_check_in_item_success_unknown_status():
    mock_client = MagicMock()
    mock_client.folio_post.return_value = {"item": {"status": {"name": "In transit"}}}
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        resp = _adapter().check_in_item("ABC123")

    assert resp.success is True
    assert resp.status is ILSCheckInStatus.UNKNOWN
    assert resp.raw_status_string == "In transit"


def test_check_in_item_defaults_service_point_when_unset():
    mock_client = MagicMock()
    mock_client.folio_post.return_value = {"item": {"status": {"name": "Available"}}}
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        _adapter(ils_service_point_id=None).check_in_item("ABC123")

    payload = mock_client.folio_post.call_args.args[1]
    assert payload["servicePointId"] == "00000000-0000-0000-0000-000000000000"


def test_check_in_item_service_point_override_takes_precedence():
    mock_client = MagicMock()
    mock_client.folio_post.return_value = {"item": {"status": {"name": "Available"}}}
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        _adapter(ils_service_point_id="sp-default").check_in_item(
            "ABC123", service_point_override="sp-building-42"
        )

    payload = mock_client.folio_post.call_args.args[1]
    assert payload["servicePointId"] == "sp-building-42"


def test_check_in_item_extracts_folio_error_message():
    mock_client = MagicMock()
    mock_client.folio_post.side_effect = _http_error(
        FolioValidationError,
        status_code=422,
        body=b'{"errors": [{"message": "Item barcode does not exist"}]}',
    )
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        resp = _adapter().check_in_item("NOPE")

    assert resp.success is False
    assert resp.status is ILSCheckInStatus.SYNC_ERROR
    assert "Item barcode does not exist" in resp.error_message


def test_check_in_item_falls_back_to_raw_message_on_non_json_error():
    mock_client = MagicMock()
    mock_client.folio_post.side_effect = _http_error(
        FolioHTTPError, status_code=500, body=b"internal error"
    )
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        resp = _adapter().check_in_item("ABC123")

    assert resp.success is False
    assert resp.status is ILSCheckInStatus.SYNC_ERROR
    assert "internal error" in resp.error_message


def test_check_in_item_handles_unexpected_exception():
    mock_client = MagicMock()
    mock_client.folio_post.side_effect = RuntimeError("boom")
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        resp = _adapter().check_in_item("ABC123")

    assert resp.success is False
    assert resp.status is ILSCheckInStatus.SYNC_ERROR
    assert resp.error_message == "boom"


# --------------------------------------------------------------------------- #
# fetch_pending_requests
# --------------------------------------------------------------------------- #
def test_fetch_pending_requests_maps_folio_requests():
    mock_client = MagicMock()
    mock_client.folio_get.return_value = [{
        "id": "req-1",
        "item": {"barcode": "ABC123"},
        "requesterId": "patron-1",
        "pickupServicePointId": "sp-1",
    }]
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        reqs = _adapter().fetch_pending_requests()

    assert len(reqs) == 1
    assert reqs[0].request_id == "req-1"
    assert reqs[0].item_barcode == "ABC123"
    assert reqs[0].patron_id == "patron-1"
    assert reqs[0].destination == "sp-1"

    query = mock_client.folio_get.call_args.kwargs["query_params"]["query"]
    assert 'pickupServicePointId=="sp-1"' in query


def test_fetch_pending_requests_empty_on_error():
    mock_client = MagicMock()
    mock_client.folio_get.side_effect = RuntimeError("boom")
    with patch("app.ils.folio_adapter.FolioClient", _mock_client_class(mock_client)):
        assert _adapter().fetch_pending_requests() == []


# --------------------------------------------------------------------------- #
# FolioClient caching — the factory builds a new FolioILSAdapter per call, so the
# underlying FolioClient (and its login) must be cached and reused across those
# short-lived instances rather than re-authenticating on every ILS operation.
# --------------------------------------------------------------------------- #
def test_client_is_cached_and_reused_across_adapter_instances():
    mock_client = MagicMock()
    mock_client.folio_get.return_value = []
    folio_client_class = _mock_client_class(mock_client)
    config_id = uuid.uuid4()

    try:
        with patch("app.ils.folio_adapter.FolioClient", folio_client_class):
            _adapter(config_id=config_id).validate_item("ABC123")
            _adapter(config_id=config_id).validate_item("XYZ789")  # fresh adapter instance

        folio_client_class.assert_called_once()
    finally:
        folio_client_cache.clear_client(config_id)


def test_client_not_cached_without_config_id():
    mock_client = MagicMock()
    mock_client.folio_get.return_value = []
    folio_client_class = _mock_client_class(mock_client)

    with patch("app.ils.folio_adapter.FolioClient", folio_client_class):
        _adapter(config_id=None).validate_item("ABC123")
        _adapter(config_id=None).validate_item("XYZ789")

    assert folio_client_class.call_count == 2


def test_get_client_logs_and_reraises_on_login_failure():
    config_id = uuid.uuid4()
    folio_client_class = MagicMock(side_effect=RuntimeError("bad credentials"))

    try:
        with patch("app.ils.folio_adapter.FolioClient", folio_client_class):
            with pytest.raises(RuntimeError, match="bad credentials"):
                _adapter(config_id=config_id)._get_client()

        # A failed login must not be cached.
        assert folio_client_cache.get_client(config_id) is None
    finally:
        folio_client_cache.clear_client(config_id)
