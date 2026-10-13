"""
Helper functions for job assignment logic.

Provides reusable functions for:
- Auto-assigning jobs to users when they start them
- Updating job status when managers assign users
- Validating assignment permissions
- No longer blocks additional users from scanning items (FETCH-1728)
"""

from sqlalchemy.orm import Session


def auto_assign_on_start(job, new_status: str, current_user_id: int):
    """
    Automatically assign job to current user when they start it.

    This allows workers to self-assign jobs from the queue without manager intervention.

    Args:
        job: The job object (AccessionJob, VerificationJob, etc.)
        new_status: The new status being set
        current_user_id: ID of the user making the request

    Returns:
        The job object (modified in place)
    """
    if new_status == "Running":
        # Auto-assign unassigned jobs to current user
        if job.assigned_user_id is None:
            job.assigned_user_id = current_user_id
            # Status will go directly from Created → Running
            # (skipping Assigned state for self-service workflow)

    return job


def update_status_on_assignment(job, new_assigned_user_id: int = None, current_status: str = None):
    """
    Update job status to 'Assigned' when manager assigns a user.
    
    This is for manager pre-assignment workflow (not self-service).
    
    Args:
        job: The job object
        new_assigned_user_id: The new assigned_user_id value (or None if being unassigned)
        current_status: The current status of the job
        
    Returns:
        The job object (modified in place)
    """
    # Only auto-update status if the job is currently in Created state
    if current_status == "Created":
        if new_assigned_user_id is not None:
            # Manager assigned a user → move to Assigned status
            job.status = "Assigned"
        else:
            # User was unassigned → revert to Created status
            # (This handles the case where assigned_user_id is being set to None)
            pass  # Keep as Created
    
    # If job was already Assigned and user is being changed, keep it as Assigned
    elif current_status == "Assigned":
        if new_assigned_user_id is None:
            # Unassigning → revert to Created
            job.status = "Created"
    
    return job


def validate_assignment_lock(job, current_user_id: int):
    """
     FETCH-1728: disabled.
    """
    return job
