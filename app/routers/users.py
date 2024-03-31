import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.users import User
from app.schemas.users import (
    UserInput,
    UserUpdateInput,
    UserListOutput,
    UserDetailWriteOutput,
    UserDetailReadOutput,
)

import traceback


router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/", response_model=Page[UserListOutput])
def get_user_list(session: Session = Depends(get_session)) -> list:
    """
    Get a paginated list of users.

    **Returns**:
    - User List Output: The paginated list of users.
    """
    return paginate(session, select(User))


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
    else:
        raise HTTPException(status_code=404, detail="Not Found")


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
        raise HTTPException(status_code=404)

    mutated_data = user.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_user, key, value)

    setattr(existing_user, "update_dt", datetime.utcnow())

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
    else:
        raise HTTPException(status_code=404)
