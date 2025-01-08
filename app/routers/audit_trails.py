from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select


from app.database.session import get_session
from app.config.exceptions import (
    NotFound,
    ValidationException,
)
from app.filter_params import SortParams
from app.schemas.audit_trails import AuditTrailListOutput, AuditTrailDetailOutput
from app.utilities import get_sorted_query
from app.models.audit_trails import AuditTrail

router = APIRouter(
    prefix="/history",
    tags=["audit tails"],
)


@router.get("/", response_model=Page[AuditTrailListOutput])
def get_audit_trails_list(
    queue: Optional[bool] = Query(default=False),
    table_names: Optional[list[str]] = Query(default=None),
    sort_params: SortParams = Depends(),
    session: Session = Depends(get_session),
) -> list:
    """
    Get a paginated list of audit trails.

    **Parameters:**
    - table_names (list[str]): A list of tables to filter by.
    - sort_params (SortParams): The sorting parameters.

    **Returns**:
    - Audit Trail List Output: The paginated list of audit trails.
    """
    # Create a query to select all audit_trails
    query = select(AuditTrail)

    if queue:
        table_names = [
            "accession_jobs",
            "verification_jobs",
            "shelving_jobs",
            "pick_lists",
            "refile_jobs",
            "withdraw_jobs",
        ]
        query = query.filter(AuditTrail.table_name.in_(table_names))

    elif table_names:
        query = query.filter(AuditTrail.table_name.in_(table_names))

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(AuditTrail, query, sort_params)

    return paginate(session, query)


@router.get("/{table_name}/{record_id}", response_model=List[AuditTrailDetailOutput])
def get_audit_trails_detail_list(
    table_name: str,
    record_id: str,
    sort_params: SortParams = Depends(),
    session: Session = Depends(get_session),
):
    """
    Get a detailed list of audit trails for a specific record.

    **Parameters:**
    - table_name (str): The name of the table.
    - record_id (str): The ID of the record.

    **Returns**:
    - Audit Trail Detail Output: The detailed list of audit trails for the record.
    """

    if not table_name:
        raise ValidationException(detail="Table name is required.")

    if not record_id:
        raise ValidationException(detail="Record ID is required.")

    query = (
        select(AuditTrail)
        .where(AuditTrail.table_name == table_name)
        .where(AuditTrail.record_id == record_id)
    )

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(AuditTrail, query, sort_params)
    else:
        sort_params.sort_by = "updated_at"
        sort_params.sort_order = "desc"
        query = get_sorted_query(AuditTrail, query, sort_params)

    results = session.exec(query).all()

    if not results:
        raise NotFound(detail="No audit trail found for the record.")

    for result in results:
        if result.updated_by == "":
            result.updated_by = "System Generated"
        if result.new_values:
            if result.new_values.get("status", None) is not None:
                result.last_action = f"Job status changed to {result.new_values.get('status')}"

    return results
