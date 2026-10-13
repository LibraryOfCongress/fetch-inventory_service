# /code/app/routers/priorities.py - REFACRORED TO SQLALCHEMY V2

from typing import Optional

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.priorities import Priority
from app.schemas.priorities import (
    PriorityInput,
    PriorityUpdateInput,
    PriorityListOutput,
    PriorityDetailWriteOutput,
    PriorityDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/requests",
    tags=["requests"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/priorities", response_model=Page[PriorityListOutput])
def get_priority_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Priority Value"),
) -> list:
    """
    Get a list of priorities
    """
    # Create a query to select all Priority
    query = select(Priority)

    if search:
        query = query.where(Priority.value.icontains(search))

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(Priority)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/priorities/{id}", response_model=PriorityDetailReadOutput)
def get_priority_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve priority details by ID
    """
    priority = session.get(Priority, id)
    if priority:
        return priority

    raise NotFound(detail=f"Priority ID {id} Not Found")


@router.post("/priorities", response_model=PriorityDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def create_priority(
    priority_input: PriorityInput, session: Session = Depends(get_session)
) -> Priority:
    """
    Create a Priority
    """
    try:
        new_priority = Priority(**priority_input.model_dump())

        # Add the new priority to the database
        session.add(new_priority)
        session.commit()
        session.refresh(new_priority)
        return new_priority

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/priorities/{id}", response_model=PriorityDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def update_priority(
    id: int, priority: PriorityUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an existing Priority
    """
    try:
        existing_priority = session.get(Priority, id)

        if existing_priority is None:
            raise NotFound(detail=f"Priority ID {id} Not Found")

        mutated_data = priority.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_priority, key, value)

        setattr(existing_priority, "update_dt", datetime.now(timezone.utc))
        session.add(existing_priority)
        session.commit()
        session.refresh(existing_priority)

        return existing_priority

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/priorities/{id}", dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def delete_priority(id: int, session: Session = Depends(get_session)):
    """
    Delete an Priority by ID
    """
    priority = session.get(Priority, id)

    if priority:
        session.delete(priority)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Priority ID {id} Not Found")
