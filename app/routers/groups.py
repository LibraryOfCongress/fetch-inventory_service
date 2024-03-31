from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.groups import Group
from app.models.users import User
from app.models.user_groups import UserGroup
from app.schemas.groups import (
    GroupInput,
    GroupUpdateInput,
    GroupListOutput,
    GroupDetailWriteOutput,
    GroupDetailReadOutput,
    GroupUserOutput,
)


router = APIRouter(
    prefix="/groups",
    tags=["groups"],
)


@router.get("/", response_model=Page[GroupListOutput])
def get_group_list(session: Session = Depends(get_session)) -> list:
    """
    Get a list of groups
    """
    return paginate(session, select(Group))


@router.get("/{id}", response_model=GroupDetailReadOutput)
def get_group_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve group by id
    """
    group = session.get(Group, id)

    if group:
        return group
    else:
        raise HTTPException(status_code=404, detail="Not Found")


@router.get("/{id}/users", response_model=GroupUserOutput)
def get_group_users(id: int, session: Session = Depends(get_session)):
    """
    Retrieve list of users belonging to a group
    """
    group = session.get(Group, id)
    if group:
        return group
    else:
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/{group_id}/add_user/{user_id}", response_model=GroupUserOutput)
def add_user_to_group(group_id: int, user_id: int, session: Session = Depends(get_session)):
    """
    Add a user to a group by group and user id
    """
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group Not Found")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User Not Found")

    new_group_user = UserGroup(group_id=group_id,user_id=user_id)
    session.add(new_group_user)
    session.commit()
    session.refresh(group)
    return group


@router.post("/", response_model=GroupDetailWriteOutput, status_code=201)
def create_group(group_input: GroupInput, session: Session = Depends(get_session)):
    """
    Create a new group
    """
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
        raise HTTPException(status_code=404)

    mutated_data = group.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_group, key, value)

    setattr(existing_group, "update_dt", datetime.utcnow())

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
        return HTTPException(status_code=204)
    else:
        raise HTTPException(status_code=404)


@router.delete("/{group_id}/remove_user/{user_id}", status_code=204)
def remove_user_from_group(group_id: int, user_id: int, session: Session = Depends(get_session)):
    """
    Remove a user from a group, by group and user id
    """
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group Not Found")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User Not Found")
    group_user = session.query(UserGroup).filter_by(group_id=group_id, user_id=user_id).first()
    if not group_user:
        raise HTTPException(status_code=404, detail="User did not belong to group")
    session.delete(group_user)
    session.commit()
    session.refresh(group)
    return group
