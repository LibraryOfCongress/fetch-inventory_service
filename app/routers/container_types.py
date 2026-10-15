# /code/app/routers/container_types.py - REFACRORED TO SQLALCHEMY V2

from typing import Optional

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Response, Query
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
from app.models.container_types import ContainerType

from app.schemas.container_types import (
    ContainerTypeInput,
    ContainerTypeListOutput,
    ContainerTypeDetailWriteOutput,
    ContainerTypeDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/container-types",
    tags=["container types"],
)


@router.get("/", response_model=Page[ContainerTypeListOutput])
def get_container_type_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Container Type Type"),
) -> list:
    """
    Retrieve a list of container types.
    """

    # Create a query to retrieve all Container Type
    query = select(ContainerType)

    if search:
        query = query.where(ContainerType.type.icontains(search))

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using RequestSorter
        sorter = BaseSorter(ContainerType)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=ContainerTypeDetailReadOutput)
def get_container_type_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve details of a specific container type by ID.
    """
    container_type = session.get(ContainerType, id)
    if container_type:
        return container_type

    raise NotFound(detail=f"Container Type ID {id} Not Found")


@router.post("/", response_model=ContainerTypeDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def create_container_type(
    container_type_input: ContainerTypeInput, session: Session = Depends(get_session)
):
    """
    Create a new container type record.'
    """
    try:
        new_container_type = ContainerType(**container_type_input.model_dump())

        session.add(new_container_type)
        session.commit()
        session.refresh(new_container_type)

        return new_container_type

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=ContainerTypeDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def update_container_type(
    id: int, container_type: ContainerTypeInput, session: Session = Depends(get_session)
):
    """
    Update an existing container type in the database.
    """
    try:
        existing_container_type = session.get(ContainerType, id)

        if not existing_container_type:
            raise NotFound(detail=f"Container Type ID {id} Not Found")

        mutated_data = container_type.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_container_type, key, value)

        setattr(existing_container_type, "update_dt", datetime.now(timezone.utc))

        session.add(existing_container_type)
        session.commit()
        session.refresh(existing_container_type)

        return existing_container_type

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", status_code=204, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def delete_container_type(id: int, session: Session = Depends(get_session)):
    """
    Deletes a container type from the database by its ID.
    """
    container_type = session.get(ContainerType, id)

    if container_type:
        session.delete(container_type)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Container Type ID {id} Not Found")