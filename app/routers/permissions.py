from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc
from datetime import datetime

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
from app.utilities import get_sorted_query

router = APIRouter(
    prefix="/permissions",
    tags=["permissions"],
)


@router.get("/", response_model=Page[PermissionListOutput])
def get_permission_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a paginated list of permissions.

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.

    **Returns**:
    - Permission List Output: The paginated list of permissions.
    """
    # Create a query to select all Permission
    query = select(Permission).distinct()

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(Permission, query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=PermissionDetailReadOutput)
def get_permission_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a permission from the database using the provided ID.

    **Args**:
    - id: The ID of the permission.

    **Returns**:
    - Permission Detail Read Output: The details of the permission.

    **Raises**:
    - HTTPException: If the permission is not found in the database.
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

    **Args**:
    - permission_input: The input data for the permission.

    **Returns**:
    - Permission Detail Write Output: The details of the created permission.

    **Raises**:
    - HTTPException: If the permission already exists in the database.
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

    **Args**:
    - id: The ID of the permission to update.
    - permission_input: The input data for the permission.

    **Returns**:
    - Permission Detail Write Output: The details of the updated permission.

    **Raises**:
    - HTTPException: If the permission is not found in the database.
    """
    # Retrieve the permission from the database using the provided ID
    existing_permission = session.get(Permission, id)

    if not existing_permission:
        raise NotFound(detail=f"Permission ID {id} Not Found")

    mutated_data = permission_input.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_permission, key, value)

    setattr(existing_permission, "update_dt", datetime.utcnow())

    return commit_record(session, existing_permission)


@router.delete("/{id}")
def delete_permission(id: int, session: Session = Depends(get_session)):
    """
    Delete a permission from the database.

    **Args**:
    - id: The ID of the permission to delete.

    **Returns**:
    - None: If the permission is deleted successfully.

    **Raises**:
    - HTTPException: If the permission is not found in the database.
    """
    permission = session.get(Permission, id)

    if permission:
        session.delete(permission)
        session.commit()
        return HTTPException(
            status_code=204, detail=f"Permission ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Permission ID {id} Not Found")
