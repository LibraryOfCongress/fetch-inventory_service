"""Unit tests for app/ils/mock_adapter.py — pure logic, no database."""
import pytest

from app.ils.interfaces import ILSCheckInStatus
from app.ils.mock_adapter import MockILSAdapter


def _adapter(**overrides):
    kwargs = dict(
        base_url="http://x", tenant_id="t",
        auth_client_id="c", auth_client_secret="s",
        expected_shelved_status="Available",
    )
    kwargs.update(overrides)
    return MockILSAdapter(**kwargs)


# --------------------------------------------------------------------------- #
# validate_item
# --------------------------------------------------------------------------- #
def test_validate_item_rejects_fail_prefix():
    assert _adapter().validate_item("FAIL-123") is False


@pytest.mark.parametrize("barcode", ["MOCK-001", "ABC123", "Item-Z"])
def test_validate_item_accepts_normal_barcodes(barcode):
    assert _adapter().validate_item(barcode) is True


# --------------------------------------------------------------------------- #
# fetch_item_metadata
# --------------------------------------------------------------------------- #
def test_fetch_metadata_for_fail_returns_unknown():
    md = _adapter().fetch_item_metadata("FAIL-999")
    assert md.title == "Unknown Item"
    assert md.is_valid_location is False
    assert md.author is None
    assert md.call_number is None
    assert md.material_type is None


def test_fetch_metadata_for_normal_uses_barcode_suffix():
    md = _adapter().fetch_item_metadata("ABC123")
    assert md.title == "Mock Title for ABC123"
    assert md.author == "Test Author"
    assert md.call_number == "QC.123.123"  # last 3 chars of "ABC123"
    assert md.material_type == "Book"
    assert md.is_valid_location is True


# --------------------------------------------------------------------------- #
# check_in_item
# --------------------------------------------------------------------------- #
def test_check_in_fail_returns_missing():
    resp = _adapter().check_in_item("FAIL-1")
    assert resp.success is False
    assert resp.status is ILSCheckInStatus.MISSING
    assert resp.raw_status_string == "Not Found"
    assert resp.error_message  # non-empty


def test_check_in_hold_returns_on_hold():
    resp = _adapter().check_in_item("HOLD-42")
    assert resp.success is True
    assert resp.status is ILSCheckInStatus.ON_HOLD
    assert resp.raw_status_string == "On hold shelf"


def test_check_in_normal_echoes_expected_shelved_status():
    # The adapter is designed to "perfectly match" whatever expected status
    # was configured, so shelving-side comparisons pass by default.
    resp = _adapter(expected_shelved_status="Available").check_in_item("MOCK-1")
    assert resp.success is True
    assert resp.status is ILSCheckInStatus.AVAILABLE
    assert resp.raw_status_string == "Available"

    resp = _adapter(expected_shelved_status="Item in place").check_in_item("MOCK-2")
    assert resp.raw_status_string == "Item in place"


def test_check_in_accepts_service_point_override():
    resp = _adapter().check_in_item("MOCK-3", service_point_override="FORT-MEADE-SP")
    assert resp.success is True


# --------------------------------------------------------------------------- #
# fetch_pending_requests
# --------------------------------------------------------------------------- #
def test_fetch_pending_requests_returns_two_mocks():
    reqs = _adapter().fetch_pending_requests()
    assert len(reqs) == 2
    ids = {r.request_id for r in reqs}
    assert ids == {"REQ-1001", "REQ-1002"}
    # Each item has the required fields populated.
    for r in reqs:
        assert r.item_barcode and r.patron_id and r.destination
