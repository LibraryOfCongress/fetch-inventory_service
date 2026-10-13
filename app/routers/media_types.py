# /code/app/routers/media_types.py - REFACRORED TO SQLALCHEMY V2

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
from app.models.media_types import MediaType

from app.schemas.media_types import (
    MediaTypeInput,
    MediaTypeListOutput,
    MediaTypeDetailWriteOutput,
    MediaTypeDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/media-types",
    tags=["media types"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/", response_model=Page[MediaTypeListOutput])
def get_media_type_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Media Type Name"),
) -> list:
    """
    Retrieve a list of media types
    """
    # Create a query to retrieve all Media Type
    query = select(MediaType)

    if search:
        query = query.where(MediaType.name.icontains(search))

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = BaseSorter(MediaType)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=MediaTypeDetailReadOutput)
def get_media_type_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a media type by its ID.
    """
    media_type = session.get(MediaType, id)
    if media_type:
        return media_type

    raise NotFound(detail=f"Media Type ID {id} Not Found")


@router.post("/", response_model=MediaTypeDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def create_media_type(
    media_type_input: MediaTypeInput, session: Session = Depends(get_session)
):
    """
    Create a new media type record.
    """
    try:
        new_media_type = MediaType(**media_type_input.model_dump())

        session.add(new_media_type)
        session.commit()
        session.refresh(new_media_type)

        return new_media_type

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=MediaTypeDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def update_media_type(
    id: int, media_type: MediaTypeInput, session: Session = Depends(get_session)
):
    """
    Update a media type record by its id.
    """
    try:
        existing_media_type = session.get(MediaType, id)

        if not existing_media_type:
            raise NotFound(detail=f"Media Type ID {id} Not Found")

        mutated_data = media_type.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_media_type, key, value)

        setattr(existing_media_type, "update_dt", datetime.now(timezone.utc))

        session.add(existing_media_type)
        session.commit()
        session.refresh(existing_media_type)

        return existing_media_type

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", status_code=204, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def delete_media_type(id: int, session: Session = Depends(get_session)):
    """
    Delete a media type by its ID.
    """
    media_type = session.get(MediaType, id)

    if media_type:
        session.delete(media_type)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Media Type ID {id} Not Found")
