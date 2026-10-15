"""Unit tests for app/utils/container_status.py — pure logic, no database."""
from types import SimpleNamespace

import pytest

from app.utils.container_status import passes_job_gate

COMPLETED = "Completed"
RUNNING = "Running"


def make_job(status=COMPLETED):
    return SimpleNamespace(status=status)


# --------------------------------------------------------------------------- #
# Legacy containers: scanned=True, no job reference -> must pass
# (regression for the "Container has not been accessioned/verified" error).
# --------------------------------------------------------------------------- #
def test_legacy_scanned_without_job_passes():
    assert passes_job_gate(
        scanned=True, job_id=None, job=None, completed_status=COMPLETED
    ) is True


def test_legacy_scanned_with_stray_job_object_still_passes():
    # job_id is the authority; a dangling job object without an id is ignored.
    assert passes_job_gate(
        scanned=True, job_id=None, job=make_job(RUNNING), completed_status=COMPLETED
    ) is True


# --------------------------------------------------------------------------- #
# Never scanned -> never passes, regardless of job state.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("job_id,job", [(None, None), (5, make_job(COMPLETED))])
def test_not_scanned_never_passes(job_id, job):
    assert passes_job_gate(
        scanned=False, job_id=job_id, job=job, completed_status=COMPLETED
    ) is False


# --------------------------------------------------------------------------- #
# Non-legacy containers: a referenced job must exist and be completed.
# --------------------------------------------------------------------------- #
def test_referenced_completed_job_passes():
    assert passes_job_gate(
        scanned=True, job_id=5, job=make_job(COMPLETED), completed_status=COMPLETED
    ) is True


def test_referenced_incomplete_job_blocks():
    assert passes_job_gate(
        scanned=True, job_id=5, job=make_job(RUNNING), completed_status=COMPLETED
    ) is False


def test_referenced_but_missing_job_blocks():
    # job_id set but the record couldn't be loaded (deleted/orphaned) -> block.
    assert passes_job_gate(
        scanned=True, job_id=5, job=None, completed_status=COMPLETED
    ) is False
