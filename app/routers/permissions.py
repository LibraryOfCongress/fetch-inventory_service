# /code/app/routers/permissions.py - REFACRORED TO SQLALCHEMY V2

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, asc, desc # select is imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.filter_params import SortParams
from app.models.permissions import Permission
from app.schemas.permissions import (
    PermissionInput,
    PermissionListOutput,
    PermissionDetailWriteOutput,
    PermissionDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/permissions",
    tags=["permissions"],
    dependencies=[Depends(RequiresPermission("can_manage_groups_and_permissions"))],
)


@router.get("/", response_model=Page[PermissionListOutput])
def get_permission_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a paginated list of permissions.
    """
    # Create a query to select all Permission
    query = select(Permission)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(Permission)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=PermissionDetailReadOutput)
def get_permission_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a permission from the database using the provided ID.
    """
    # Retrieve the permission from the database using the provided ID
    permission = session.get(Permission, id)

    if not permission:
        raise NotFound(detail=f"Permission ID {id} Not Found")

    return permission


@router.post("/", response_model=PermissionDetailWriteOutput, status_code=201)
def create_permission(
    permission_input: PermissionInput, session: Session = Depends(get_session)
):
    """
    Create a new permission in the database.
    """
    try:
        permission = Permission(**permission_input.model_dump())

        return commit_record(session, permission)  # Return the created permission
    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=PermissionDetailWriteOutput)
def update_permission(
    id: int, permission_input: PermissionInput, session: Session = Depends(get_session)
):
    """
    Update an existing permission in the database.
    """
    # Retrieve the permission from the database using the provided ID
    existing_permission = session.get(Permission, id)

    if not existing_permission:
        raise NotFound(detail=f"Permission ID {id} Not Found")

    mutated_data = permission_input.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_permission, key, value)

    setattr(existing_permission, "update_dt", datetime.now(timezone.utc))

    return commit_record(session, existing_permission)


@router.delete("/{id}")
def delete_permission(id: int, session: Session = Depends(get_session)):
    """
    Delete a permission from the database.
    """
    permission = session.get(Permission, id)

    if permission:
        session.delete(permission)
        session.commit()
        return Response(status_code=204)

    raise NotFound(detail=f"Permission ID {id} Not Found")
