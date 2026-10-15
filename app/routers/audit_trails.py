# /code/app/routers/audit_trails.py - Simplified for app-level audit logging

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List

from app.database.session import get_session
from app.config.exceptions import NotFound, ValidationException
from app.filter_params import SortParams
from app.schemas.audit_trails import AuditTrailListOutput, AuditTrailDetailOutput
from app.sorting import BaseSorter
from app.models.audit_trails import AuditTrail

from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/history",
    tags=["audit trails"],
    dependencies=[Depends(RequiresPermission("can_view_audit_logs"))],
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
    """
    query = select(AuditTrail)

    if queue:
        job_table_names = [
            "accession_jobs",
            "verification_jobs",
            "shelving_jobs",
            "pick_lists",
            "refile_jobs",
            "withdraw_jobs",
            "shipping_jobs",
        ]
        query = query.filter(AuditTrail.table_name.in_(job_table_names))

    elif table_names:
        query = query.filter(AuditTrail.table_name.in_(table_names))

    if sort_params.sort_by:
        sorter = BaseSorter(AuditTrail)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{table_name}/{record_id}", response_model=List[AuditTrailDetailOutput])
def get_audit_trails_detail_list(
    table_name: str,
    record_id: str,
    sort_params: SortParams = Depends(),
    session: Session = Depends(get_session),
):
    """
    Get audit trail entries for a specific job.
    Queries by job_type + job_id (new app-level fields), falling back to
    table_name + record_id for backward compatibility with older data.
    """
    if not table_name:
        raise ValidationException(detail="Table name is required.")
    if not record_id:
        raise ValidationException(detail="Record ID is required.")

    # Query by new app-level fields first, then fall back to legacy fields
    query = select(AuditTrail).where(
        (
            (AuditTrail.job_type == table_name) & (AuditTrail.job_id == record_id)
        ) | (
            (AuditTrail.table_name == table_name) & (AuditTrail.record_id == record_id)
        )
    )

    if not sort_params.sort_by:
        sort_params.sort_by = "updated_at"
        sort_params.sort_order = "desc"

    sorter = BaseSorter(AuditTrail)
    query = sorter.apply_sorting(query, sort_params)

    logs = session.execute(query).scalars().all()

    # Map description → last_action for frontend compatibility
    results = []
    for log in logs:
        detail = AuditTrailDetailOutput(
            id=log.id,
            table_name=log.table_name,
            record_id=log.record_id,
            operation_type=log.operation_type,
            event_type=log.event_type,
            description=log.description,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            job_type=log.job_type,
            job_id=log.job_id,
            updated_by=log.updated_by,
            updated_at=log.updated_at,
            last_action=log.description or log.last_action,
            original_values=log.original_values,
            new_values=log.new_values,
        )
        results.append(detail)

    return results


@router.get("/entity/{entity_type}/{entity_id}", response_model=List[AuditTrailDetailOutput])
def get_entity_history(
    entity_type: str,
    entity_id: str,
    sort_params: SortParams = Depends(),
    session: Session = Depends(get_session),
):
    """
    Get audit trail entries for a specific entity (item, tray, shelf, non_tray_item).
    Returns all history for that entity across all jobs.
    """
    if not entity_type:
        raise ValidationException(detail="Entity type is required.")
    if not entity_id:
        raise ValidationException(detail="Entity ID is required.")

    query = select(AuditTrail).where(
        AuditTrail.entity_type == entity_type,
        AuditTrail.entity_id == entity_id,
    )

    if not sort_params.sort_by:
        sort_params.sort_by = "updated_at"
        sort_params.sort_order = "desc"

    sorter = BaseSorter(AuditTrail)
    query = sorter.apply_sorting(query, sort_params)

    logs = session.execute(query).scalars().all()

    results = []
    for log in logs:
        detail = AuditTrailDetailOutput(
            id=log.id,
            table_name=log.table_name,
            record_id=log.record_id,
            operation_type=log.operation_type,
            event_type=log.event_type,
            description=log.description,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            job_type=log.job_type,
            job_id=log.job_id,
            updated_by=log.updated_by,
            updated_at=log.updated_at,
            last_action=log.description or log.last_action,
            original_values=log.original_values,
            new_values=log.new_values,
        )
        results.append(detail)

    return results