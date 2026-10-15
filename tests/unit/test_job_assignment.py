"""Unit tests for app/utils/job_assignment.py — pure logic, no database."""
from types import SimpleNamespace

import pytest

from app.utils.job_assignment import (
    auto_assign_on_start,
    update_status_on_assignment,
    validate_assignment_lock,
)


def make_job(assigned_user_id=None, status=None):
    return SimpleNamespace(assigned_user_id=assigned_user_id, status=status)


# --------------------------------------------------------------------------- #
# auto_assign_on_start
# --------------------------------------------------------------------------- #
def test_auto_assign_claims_unassigned_job_on_start():
    job = make_job(assigned_user_id=None)
    auto_assign_on_start(job, new_status="Running", current_user_id=42)
    assert job.assigned_user_id == 42


def test_auto_assign_noop_when_already_owned_by_current_user():
    job = make_job(assigned_user_id=42)
    auto_assign_on_start(job, new_status="Running", current_user_id=42)
    assert job.assigned_user_id == 42


def test_auto_assign_allows_starting_job_owned_by_other_user():
    job = make_job(assigned_user_id=7)
    auto_assign_on_start(job, new_status="Running", current_user_id=42)
    assert job.assigned_user_id == 7


@pytest.mark.parametrize("new_status", ["Paused", "Completed", "Assigned"])
def test_auto_assign_only_acts_on_running(new_status):
    job = make_job(assigned_user_id=None)
    auto_assign_on_start(job, new_status=new_status, current_user_id=42)
    assert job.assigned_user_id is None


def test_auto_assign_skips_lock_check_when_not_running():
    # Assigned to another user, but status isn't Running → no Forbidden raised.
    job = make_job(assigned_user_id=7)
    auto_assign_on_start(job, new_status="Paused", current_user_id=42)
    assert job.assigned_user_id == 7


# --------------------------------------------------------------------------- #
# update_status_on_assignment
# --------------------------------------------------------------------------- #
def test_created_to_assigned_when_user_assigned():
    job = make_job(status="Created")
    update_status_on_assignment(job, new_assigned_user_id=5, current_status="Created")
    assert job.status == "Assigned"


def test_created_stays_created_when_unassigned():
    job = make_job(status="Created")
    update_status_on_assignment(job, new_assigned_user_id=None, current_status="Created")
    assert job.status == "Created"


def test_assigned_reverts_to_created_when_unassigned():
    job = make_job(status="Assigned")
    update_status_on_assignment(job, new_assigned_user_id=None, current_status="Assigned")
    assert job.status == "Created"


def test_assigned_stays_assigned_when_reassigned():
    job = make_job(status="Assigned")
    update_status_on_assignment(job, new_assigned_user_id=9, current_status="Assigned")
    assert job.status == "Assigned"


@pytest.mark.parametrize("current", ["Running", "Paused", "Completed"])
def test_status_unchanged_for_other_states(current):
    job = make_job(status=current)
    update_status_on_assignment(job, new_assigned_user_id=9, current_status=current)
    assert job.status == current


# --------------------------------------------------------------------------- #
# validate_assignment_lock
# --------------------------------------------------------------------------- #
def test_lock_allows_unassigned_job():
    validate_assignment_lock(make_job(assigned_user_id=None), current_user_id=42)


def test_lock_allows_owner():
    validate_assignment_lock(make_job(assigned_user_id=42), current_user_id=42)


def test_lock_allows_non_owner():
    validate_assignment_lock(make_job(assigned_user_id=7), current_user_id=42)
