# /code/app/routers/groups.py - RECONSTRUCTED AND CORRECTED

from fastapi import APIRouter, HTTPException, Depends, status
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination import Page
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, asc, desc, and_ # select is imported from sqlalchemy now
from datetime import datetime, timezone

from app.database.session import get_session, commit_record, remove_record
from app.filter_params import SortParams
from app.models.groups import Group, GroupPermission
from app.models.permissions import Permission
from app.models.users import User
from app.models.user_groups import UserGroup
from app.config.exceptions import (
    NotFound
)
from app.schemas.groups import (
    GroupInput,
    GroupUpdateInput,
    GroupListOutput,
    GroupDetailWriteOutput,
    GroupDetailReadOutput,
    GroupUserOutput,
    GroupPermissionsOutput,
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/groups",
    tags=["groups"],
    dependencies=[Depends(RequiresPermission("can_manage_groups_and_permissions"))],
)


@router.get("/", response_model=Page[GroupListOutput])
def get_group_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a list of groups
    """

    # Create a query to retrieve all Groups
    query = select(Group)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = BaseSorter(Group)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=GroupDetailReadOutput)
def get_group_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve group by id
    """
    group = session.get(Group, id)

    if group:
        return group

    raise NotFound(detail=f"Group ID {id} Not Found")


@router.post("/", response_model=GroupDetailWriteOutput, status_code=201)
def create_group(group_input: GroupInput, session: Session = Depends(get_session)):
    """
    Create a new group
    """
    # Check if a group with the same name already exists
    existing_group = session.execute(select(Group).where(Group.name == group_input.name)).scalars().first()
    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group with name '{group_input.name}' already exists"
        )

    new_group = Group(**group_input.model_dump())
    session.add(new_group)
    session.commit()
    session.refresh(new_group)

    return new_group


@router.patch("/{id}", response_model=GroupDetailWriteOutput)
def update_group(
    id: int, group: GroupUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a group by id
    """
    existing_group = session.get(Group, id)

    if not existing_group:
        raise NotFound(detail=f"Group ID {id} Not Found")

    mutated_data = group.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_group, key, value)

    setattr(existing_group, "update_dt", datetime.now(timezone.utc))

    session.add(existing_group)
    session.commit()
    session.refresh(existing_group)

    return existing_group


@router.delete("/{id}")
def delete_group(id: int, session: Session = Depends(get_session)):
    """
    Delete a group by id
    """
    group = session.get(Group, id)

    if group:
        session.delete(group)
        session.commit()
        return HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"Group id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Group ID {id} Not Found")


@router.get("/{id}/users", response_model=GroupUserOutput)
def get_group_users(id: int, session: Session = Depends(get_session)):
    """
    Retrieve list of users belonging to a group
    """
    group = session.get(Group, id)
    if group:
        return group

    raise NotFound(detail=f"Group ID {id} Not Found")


@router.post("/{group_id}/add_user/{user_id}", response_model=GroupUserOutput)
def add_user_to_group(
    group_id: int, user_id: int, session: Session = Depends(get_session)
):
    """
    Add a user to a group by group and user id
    """
    group = session.get(Group, group_id)

    if not group:
        raise NotFound(detail=f"Group ID {group_id} Not Found")

    user = session.get(User, user_id)

    if not user:
        raise NotFound(detail=f"User ID {user_id} Not Found")

    new_group_user = UserGroup(group_id=group_id, user_id=user_id)

    commit_record(session, new_group_user)
    session.refresh(group)

    return group


@router.delete("/{group_id}/remove_user/{user_id}", response_model=GroupUserOutput)
def remove_user_from_group(
    group_id: int, user_id: int, session: Session = Depends(get_session)
):
    """
    Remove a user from a group, by group and user id
    """
    group = session.get(Group, group_id)

    if not group:
        raise NotFound(detail=f"Group ID {group_id} Not Found")

    user = session.get(User, user_id)

    if not user:
        raise NotFound(detail=f"User ID {user_id} Not Found")

    # CRITICAL V2 FIX: session.query().filter_by().first() -> session.execute(select(...)).scalars().first()
    group_user = (
        session.execute(select(UserGroup).where(and_(UserGroup.group_id == group_id, UserGroup.user_id == user_id)))
        .scalars()
        .first()
    )

    if not group_user:
        raise NotFound(detail="User did not belong to group")

    remove_record(session, group_user)
    session.refresh(group)

    return group


@router.get("/{group_id}/permissions", response_model=GroupPermissionsOutput)
def get_group_permissions(group_id: int, session: Session = Depends(get_session)):
    """
    Get a list of permissions for a group
    """
    group = session.get(Group, group_id)

    if group:
        return group

    raise NotFound(detail=f"Group ID {group_id} Not Found")


@router.post(
    "/{group_id}/add_permission/{permission_id}",
    response_model=GroupPermissionsOutput,
)
def add_permission_to_group(
    group_id: int, permission_id: int, session: Session = Depends(get_session)
):
    """
    Add a permission to a group by group and permission id

    **Args:**
    - group_id: The ID of the group.
    - permission_id: The ID of the permission.

    **Returns:**
    - Group Permissions Output: A list of permissions for a group.

    **Raises:**
    - NotFound: If the group is not found in the database.
    - NotFound: If the permission is not found in the database.
    - HTTPException: If the group or permission is not found in the database.
    - HTTPException: If the group already has the permission.
    - HTTPException: If the permission already belongs to the group.
    """
    group = session.get(Group, group_id)

    if not group:
        raise NotFound(detail=f"Group ID {group_id} Not Found")

    permission = session.get(Permission, permission_id)

    if not permission:
        raise NotFound(detail=f"Permission ID {permission_id} Not Found")

    new_group_permission = GroupPermission(
        group_id=group_id, permission_id=permission_id
    )

    commit_record(session, new_group_permission)
    session.refresh(group)

    return group


@router.delete(
    "/{group_id}/remove_permission/{permission_id}",
    response_model=GroupPermissionsOutput,
)
def remove_permission_from_group(
    group_id: int, permission_id: int, session: Session = Depends(get_session)
):
    """
    Remove a permission from a group, by group and user id

    **Args:**
    - group_id: The ID of the group.
    - permission_id: The ID of the permission.

    **Returns:**
    - Group Permissions Output: A list of permissions for a group.

    **Raises:**
    - NotFound: If the group is not found in the database.
    - NotFound: If the permission is not found in the database.
    - HTTPException: If the group is not found in the database.
    - HTTPException: If the permission is not found in the database.
    - HTTPException: If the permission is not associated with the group.
    """
    group = session.get(Group, group_id)

    if not group:
        raise NotFound(detail=f"Group ID {group_id} Not Found")

    permission = session.get(Permission, permission_id)

    if not permission:
        raise NotFound(detail=f"Permission ID {permission_id} Not Found")

    # CRITICAL V2 FIX: session.query().filter_by().first() -> session.execute(select(...)).scalars().first()
    group_permission = (
        session.execute(select(GroupPermission).where(and_(GroupPermission.group_id == group_id, GroupPermission.permission_id == permission_id)))
        .scalars()
        .first()
    )

    if not group_permission:
        raise NotFound(detail="Permission did not belong to group")

    remove_record(session, group_permission)
    session.refresh(group)

    return group