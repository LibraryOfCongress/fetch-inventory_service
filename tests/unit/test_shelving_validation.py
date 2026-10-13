"""Unit tests for the pure shelving-list validation rules — no database."""
import pytest

from app.services.shelving_assignment import evaluate_container_validation


def _valid_kwargs(**overrides):
    base = dict(
        container_type="Tray",
        container_id=1,
        barcode_value="BC-1",
        shelf_position_id=None,
        verification_job_id=10,
        verification_completed=True,
        conflicting_shelving_job_id=None,
        owner_id=3,
        owner_name="Owner A",
        size_class_id=4,
        size_class_name="Letter",
    )
    base.update(overrides)
    return base


def test_valid_container_passes_all_gates():
    result = evaluate_container_validation(**_valid_kwargs())
    assert result.is_valid is True
    assert result.error_message is None
    assert result.container_type == "Tray"
    assert result.container_id == 1
    assert result.barcode_value == "BC-1"
    assert result.owner_id == 3
    assert result.owner_name == "Owner A"
    assert result.size_class_id == 4
    assert result.size_class_name == "Letter"
    assert result.verification_job_id == 10


def test_already_shelved_is_invalid():
    result = evaluate_container_validation(**_valid_kwargs(shelf_position_id=99))
    assert result.is_valid is False
    assert result.error_message == "Barcode BC-1 is already shelved"


def test_already_shelved_takes_precedence_over_verification():
    result = evaluate_container_validation(
        **_valid_kwargs(
            shelf_position_id=99, verification_job_id=None, verification_completed=False
        )
    )
    assert result.is_valid is False
    assert result.error_message == "Barcode BC-1 is already shelved"


def test_missing_verification_job_is_invalid():
    result = evaluate_container_validation(
        **_valid_kwargs(verification_job_id=None, verification_completed=False)
    )
    assert result.is_valid is False
    assert result.error_message == "Barcode BC-1 has not completed verification"


def test_incomplete_verification_is_invalid():
    result = evaluate_container_validation(**_valid_kwargs(verification_completed=False))
    assert result.is_valid is False
    assert result.error_message == "Barcode BC-1 has not completed verification"


def test_conflicting_active_shelving_job_is_invalid():
    result = evaluate_container_validation(**_valid_kwargs(conflicting_shelving_job_id=7))
    assert result.is_valid is False
    assert result.error_message == "Barcode BC-1 is on Shelving Job #7"


def test_verification_check_precedes_conflict_check():
    # Both verification-incomplete and a conflicting job → verification wins (checked first).
    result = evaluate_container_validation(
        **_valid_kwargs(verification_completed=False, conflicting_shelving_job_id=7)
    )
    assert result.error_message == "Barcode BC-1 has not completed verification"


@pytest.mark.parametrize("container_type", ["Tray", "NonTray"])
def test_container_type_passthrough_on_failure(container_type):
    result = evaluate_container_validation(
        **_valid_kwargs(container_type=container_type, shelf_position_id=5)
    )
    assert result.container_type == container_type
    assert result.container_id == 1
    assert result.is_valid is False
