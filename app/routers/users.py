import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlmodel import Session, select
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
    UserListOutput,
    UserDetailWriteOutput,
    UserDetailReadOutput,
    UserGroupOutput,
    UserPermissionsOutput,
)

import traceback

from app.sorting import BaseSorter

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/", response_model=Page[UserListOutput])
def get_user_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by User Name"),
) -> list:
    """
    Get a paginated list of users.

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.
    - search: (Optional[str]): The search query.
        - Name: The name of the user to search for.

    **Returns**:
    - User List Output: The paginated list of users.
    """
    # Create a query to select all User from the database
    query = select(User)

    if search:
        query = query.where(func.concat(User.first_name, " ", User.last_name).contains(search))

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(User)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=UserDetailReadOutput)
def get_user_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a user from the database using the provided ID.

    **Args**:
    - id: The ID of the user.

    **Returns**:
    - User Detail Read Output: The details of the user.

    **Raises**:
    - HTTPException: If the user is not found in the database.
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
def create_user(user_input: UserInput, session: Session = Depends(get_session)):
    """
    Create a new user.

    **Args**:
    - User Input: The input data for creating a new user.

    **Returns**:
    - User Detail Write Output: The created user.
    """
    # Create a new User object
    new_user = User(**user_input.model_dump())
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return new_user


@router.patch("/{id}", response_model=UserDetailWriteOutput)
def update_user(
    id: int, user: UserUpdateInput, session: Session = Depends(get_session)
):
    """
    Updates a user with the given ID using the provided user data.

    **Args**:
    - id: The ID of the user to update.
    - User Update Input: The updated user data.

    **Returns**:
    - User Detail Write Output: The updated user.
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
def delete_user(id: int, session: Session = Depends(get_session)):
    """
    Delete a user with the given id.

    **Args**:
    - id: The id of the user to be deleted.

    **Returns**:
    - None: If the user is deleted successfully.

    **Raises**:
    - HTTPException: If the user is not found.
    """
    user = session.get(User, id)

    if user:
        session.delete(user)
        session.commit()
        return HTTPException(status_code=204)

    raise NotFound(detail=f"User ID {id} Not Found")


@router.get("/{user_id}/permissions", response_model=UserPermissionsOutput)
def get_user_permissions(user_id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a user from the database using the provided ID.

    **Args**:
    - user_id: The ID of the user.

    **Returns**:
    - User Detail Read Output: The details of the user.

    **Raises**:
    - HTTPException: If the user is not found in the database.
    """
    user = session.get(User, user_id)

    if not user:
        raise NotFound(status_code=404, detail="User not found")

    # Retrieve the user from the database using the provided ID
    user_groups = (
        session.exec(
            select(Group)
            .where(Group.users.any(id=user_id))
            .options(joinedload(Group.permissions))
        )
        .unique()
        .all()
    )  # Use unique().all() instead of all()

    # Aggregate all unique permissions from the user's groups
    permissions_set = {
        permission.name for group in user_groups for permission in group.permissions
    }

    if user_groups:
        return UserPermissionsOutput(id=user_id, permissions=list(permissions_set))

    raise NotFound(detail=f"User ID {user_id} Not Found")
