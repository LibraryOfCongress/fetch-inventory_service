# from fastapi import Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobFilterParams(BaseModel):
    """
    Reusable query params across Jobs.
    Status is not included as the Enumerated options differ per job.
    """
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None
    user_id: Optional[int] = None
    workflow_id: Optional[int] = None
    created_by_id: Optional[int] = None


class ShelvingJobDiscrepancyParams(BaseModel):
    """
    Query params for Shelving Job Discrepancies
    """
    shelving_job_id: Optional[int] = None
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None
    user_id: Optional[int] = None
