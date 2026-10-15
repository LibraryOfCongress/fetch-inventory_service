# /code/app/routers/users.py - REFACRORED TO SQLALCHEMY V2

import logging
from typing import Optional, List

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, func # select/func imported from sqlalchemy now
from sqlalchemy.orm import joinedload # joinedload is already correct
from datetime import datetime, timezone

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.groups import Group
from app.models.users import User
from app.config.exceptions import (
    NotFound,
)
from app.schemas.users import (
    UserInput,
    UserUpdateInput,
    UserSelfUpdateInput,
    UserListOutput,
    UserDetailWriteOutput,
    UserDetailReadOutput,
    UserGroupOutput,
    UserPermissionsOutput,
)

import traceback

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.sorting import BaseSorter, UserSorter

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/", response_model=Page[UserListOutput])
def get_user_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by User Name"),
) -> list:
    """
    Get a paginated list of users.
    """
    # Create a query to select all User from the database
    query = select(User)

    if search:
        query = query.where(func.concat(User.first_name, " ", User.last_name).icontains(search))

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = UserSorter(User)
        query = sorter.apply_sorting(query, sort_params)

    # CRITICAL FIX: Paginate now takes only the query object
    return paginate(session, query)


@router.patch("/me", response_model=UserDetailWriteOutput)
def update_own_profile(
    profile: UserSelfUpdateInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Self-service profile update for the currently authenticated user.

    Authenticated-only (no admin permission): a user may update a restricted set
    of their OWN settings (currently the default building) from the Settings
    screen. This exists so ordinary staff can set a default building without the
    admin-only ``can_manage_groups_and_permissions`` that gates ``PATCH /{id}``.

    Declared BEFORE ``/{id}`` so a PATCH to ``/users/me`` isn't captured by the
    ``/{id}`` route and rejected as a non-integer id.
    """
    # current_user is the authenticated user (guaranteed to exist); mutate only
    # the whitelisted fields present on the restricted schema.
    mutated_data = profile.model_dump(exclude_unset=True)
    for key, value in mutated_data.items():
        setattr(current_user, key, value)

    setattr(current_user, "update_dt", datetime.now(timezone.utc))

    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return current_user


@router.get("/{id}", response_model=UserDetailReadOutput)
def get_user_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a user from the database using the provided ID.
    """
    # Retrieve the user from the database using the provided ID
    user = session.get(User, id)

    if user:
        return user

    raise NotFound(detail=f"User ID {id} Not Found")


@router.get("/{id}/groups", response_model=UserGroupOutput)
def get_user_groups(id: int, session: Session = Depends(get_session)):
    """
    Retrieve list of groups a user belongs to
    """
    user = session.get(User, id)
    if user:
        return user

    raise NotFound(detail=f"User ID {id} Not Found")


@router.post("/", response_model=UserDetailWriteOutput, status_code=201)
def create_user(
    user_input: UserInput, 
    session: Session = Depends(get_session),
    _: bool = Depends(RequiresPermission("can_manage_groups_and_permissions"))
):
    """
    Create a new user.
    """
    # Create a new User object
    new_user = User(**user_input.model_dump())
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return new_user


@router.patch("/{id}", response_model=UserDetailWriteOutput)
def update_user(
    id: int, 
    user: UserUpdateInput, 
    session: Session = Depends(get_session),
    _: bool = Depends(RequiresPermission("can_manage_groups_and_permissions"))
):
    """
    Updates a user with the given ID using the provided user data.
    """
    # Get the existing user
    existing_user = session.get(User, id)

    if not existing_user:
        raise NotFound(detail=f"User ID {id} Not Found")

    mutated_data = user.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_user, key, value)

    setattr(existing_user, "update_dt", datetime.now(timezone.utc))

    session.add(existing_user)
    session.commit()
    session.refresh(existing_user)

    return existing_user


@router.delete("/{id}")
def delete_user(
    id: int, 
    session: Session = Depends(get_session),
    _: bool = Depends(RequiresPermission("can_manage_groups_and_permissions"))
):
    """
    Delete a user with the given id.
    """
    user = session.get(User, id)

    if user:
        session.delete(user)
        session.commit()
        return Response(status_code=204)

    raise NotFound(detail=f"User ID {id} Not Found")


@router.get("/{user_id}/permissions", response_model=UserPermissionsOutput)
def get_user_permissions(user_id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a user from the database using the provided ID.
    """
    user = session.get(User, user_id)

    if not user:
        raise NotFound(detail=f"User ID {user_id} Not Found")

    # Retrieve the user from the database using the provided ID
    # CRITICAL V2 FIX: session.exec().unique().all() -> session.execute(select(...)).unique().scalars().all()
    user_groups = (
        session.execute(
            select(Group)
            .where(Group.users.any(id=user_id))
            .options(joinedload(Group.permissions))
        )
        .unique()
        .scalars()
        .all()
    )

    # Aggregate all unique permissions from the user's groups
    permissions_set = {
        permission.name for group in user_groups for permission in group.permissions
    }

    if user_groups:
        return UserPermissionsOutput(id=user_id, permissions=list(permissions_set))

    raise NotFound(detail=f"User ID {user_id} Not Found")