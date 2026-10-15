"""Unit tests for the pure validators/helpers in app/utilities.py — no database."""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytz

from app.utilities import (
    _map_values_to_ids,
    _validate_item_status,
    _validate_withdraw_job_existing_item,
    is_tz_naive,
    make_aware,
    manage_transition,
    validate_container_not_shelved,
    validate_item_not_shelved,
)


# --------------------------------------------------------------------------- #
# make_aware / is_tz_naive
# --------------------------------------------------------------------------- #
def test_make_aware_localizes_naive_to_utc():
    dt = datetime(2026, 1, 1, 12, 0, 0)
    result = make_aware(dt)
    assert result.tzinfo is not None
    assert result == pytz.utc.localize(dt)


def test_make_aware_leaves_aware_unchanged():
    dt = pytz.utc.localize(datetime(2026, 1, 1, 12, 0, 0))
    assert make_aware(dt) is dt


def test_is_tz_naive_true_for_naive():
    assert is_tz_naive(datetime(2026, 1, 1)) is True


def test_is_tz_naive_false_for_aware():
    assert is_tz_naive(pytz.utc.localize(datetime(2026, 1, 1))) is False


# --------------------------------------------------------------------------- #
# _map_values_to_ids
# --------------------------------------------------------------------------- #
def test_map_values_to_ids_basic():
    rows = [SimpleNamespace(value="A", id=1), SimpleNamespace(value="B", id=2)]
    assert _map_values_to_ids(rows, "value", "id") == {"A": 1, "B": 2}


def test_map_values_to_ids_empty():
    assert _map_values_to_ids([], "value", "id") == {}


def test_map_values_to_ids_duplicate_key_last_wins():
    rows = [SimpleNamespace(value="A", id=1), SimpleNamespace(value="A", id=9)]
    assert _map_values_to_ids(rows, "value", "id") == {"A": 9}


# --------------------------------------------------------------------------- #
# _validate_withdraw_job_existing_item
# --------------------------------------------------------------------------- #
def test_existing_withdraw_empty_is_false():
    assert _validate_withdraw_job_existing_item([], 1, "Completed") is False


def test_existing_withdraw_same_job_ignored():
    items = [SimpleNamespace(id=1, status="Created")]
    assert _validate_withdraw_job_existing_item(items, 1, "Completed") is False


def test_existing_withdraw_other_active_job_is_true():
    items = [SimpleNamespace(id=2, status="Created")]
    assert _validate_withdraw_job_existing_item(items, 1, "Completed") is True


def test_existing_withdraw_other_completed_job_is_false():
    items = [SimpleNamespace(id=2, status="Completed")]
    assert _validate_withdraw_job_existing_item(items, 1, "Completed") is False


# --------------------------------------------------------------------------- #
# _validate_item_status
# --------------------------------------------------------------------------- #
def test_validate_item_status_withdrawn_appends_error():
    errors = []
    _validate_item_status(SimpleNamespace(status="Withdrawn"), 3, errors, "bad")
    assert errors == [{"line": 3, "error": "bad"}]


def test_validate_item_status_requested_appends_and_coerces_index():
    errors = []
    _validate_item_status(SimpleNamespace(status="Requested"), "5", errors, "bad")
    assert errors == [{"line": 5, "error": "bad"}]


def test_validate_item_status_valid_status_no_error():
    errors = []
    _validate_item_status(SimpleNamespace(status="In"), 1, errors, "bad")
    assert errors == []


# --------------------------------------------------------------------------- #
# validate_item_not_shelved
# --------------------------------------------------------------------------- #
def test_item_not_shelved_when_no_position():
    assert validate_item_not_shelved(None) is True


def test_item_not_shelved_when_tray_not_scanned():
    sp = SimpleNamespace(tray=SimpleNamespace(scanned_for_shelving=False))
    assert validate_item_not_shelved(sp) is True


def test_item_shelved_when_tray_scanned():
    sp = SimpleNamespace(tray=SimpleNamespace(scanned_for_shelving=True))
    assert validate_item_not_shelved(sp) is False


# --------------------------------------------------------------------------- #
# validate_container_not_shelved
# --------------------------------------------------------------------------- #
def test_container_not_shelved_when_none():
    assert validate_container_not_shelved(None) is True


def test_container_not_shelved_when_no_position_id():
    item = SimpleNamespace(shelf_position_id=None, scanned_for_shelving=True)
    assert validate_container_not_shelved(item) is True


def test_container_not_shelved_when_not_scanned():
    item = SimpleNamespace(shelf_position_id=5, scanned_for_shelving=False)
    assert validate_container_not_shelved(item) is True


def test_container_shelved_when_position_and_scanned():
    item = SimpleNamespace(shelf_position_id=5, scanned_for_shelving=True)
    assert validate_container_not_shelved(item) is False


# --------------------------------------------------------------------------- #
# manage_transition
# --------------------------------------------------------------------------- #
def test_manage_transition_running_to_paused_uses_last_transition():
    base = datetime(2026, 1, 1, 10, 0, 0)
    original = SimpleNamespace(
        status="Running",
        run_time=timedelta(minutes=5),
        last_transition=base,
        create_dt=datetime(2026, 1, 1, 9, 0, 0),
    )
    update = SimpleNamespace(status="Paused", run_timestamp=base + timedelta(minutes=10))
    result = manage_transition(original, update)
    assert result.run_time == timedelta(minutes=15)
    assert result.last_transition == make_aware(update.run_timestamp)


def test_manage_transition_uses_create_dt_when_no_last_transition():
    create = datetime(2026, 1, 1, 9, 0, 0)
    original = SimpleNamespace(
        status="Running", run_time=None, last_transition=None, create_dt=create
    )
    update = SimpleNamespace(
        status="Completed", run_timestamp=create + timedelta(minutes=30)
    )
    result = manage_transition(original, update)
    assert result.run_time == timedelta(minutes=30)


def test_manage_transition_running_to_canceled():
    base = datetime(2026, 1, 1, 10, 0, 0)
    original = SimpleNamespace(
        status="Running",
        run_time=timedelta(0),
        last_transition=base,
        create_dt=datetime(2026, 1, 1, 9, 0, 0),
    )
    update = SimpleNamespace(status="Canceled", run_timestamp=base + timedelta(minutes=20))
    result = manage_transition(original, update)
    assert result.run_time == timedelta(minutes=20)


def test_manage_transition_noop_for_unqualified_transition():
    original = SimpleNamespace(
        status="Created",
        run_time=timedelta(minutes=2),
        last_transition=None,
        create_dt=datetime(2026, 1, 1, 9, 0, 0),
    )
    update = SimpleNamespace(status="Running", run_timestamp=datetime(2026, 1, 1, 10, 0, 0))
    result = manage_transition(original, update)
    assert result.run_time == timedelta(minutes=2)
    assert result.last_transition is None


def test_manage_transition_initializes_none_run_time_even_on_noop():
    original = SimpleNamespace(
        status="Paused",
        run_time=None,
        last_transition=None,
        create_dt=datetime(2026, 1, 1, 9, 0, 0),
    )
    update = SimpleNamespace(status="Running", run_timestamp=datetime(2026, 1, 1, 10, 0, 0))
    result = manage_transition(original, update)
    assert result.run_time == timedelta(0)
