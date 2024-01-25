from fastapi import APIRouter, HTTPException, Depends, Response
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.media_types import MediaType

from app.schemas.media_types import (
    MediaTypeInput,
    MediaTypeListOutput,
    MediaTypeDetailWriteOutput,
    MediaTypeDetailReadOutput,
)

router = APIRouter(
    prefix="/media-types",
    tags=["media types"],
)


@router.get("/", response_model=Page[MediaTypeListOutput])
def get_media_type_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a list of media types
    """
    return paginate(session, select(MediaType))


@router.get("/{id}", response_model=MediaTypeDetailReadOutput)
def get_media_type_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a media type by its ID.
    """
    media_type = session.get(MediaType, id)
    if media_type is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return media_type


@router.post("/", response_model=MediaTypeDetailWriteOutput, status_code=201)
def create_media_type(media_type_input: MediaTypeInput, session: Session = Depends(get_session)):
    """
    Create a new media type record.

    **type**: Required varchar 25
    """
    new_media_type = MediaType(**media_type_input.model_dump())

    session.add(new_media_type)
    session.commit()
    session.refresh(new_media_type)

    return new_media_type


@router.patch("/{id}", response_model=MediaTypeDetailWriteOutput)
def update_media_type(id: int, media_type: MediaTypeInput, session: Session = Depends(get_session)):
    """
    Update a media type record by its id.
    """
    existing_media_type = session.get(MediaType, id)

    if not existing_media_type:
        raise HTTPException(status_code=404, detail="Not found")

    mutated_data = media_type.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_media_type, key, value)

    setattr(existing_media_type, "update_dt", datetime.utcnow())

    session.add(existing_media_type)
    session.commit()
    session.refresh(existing_media_type)
    return existing_media_type


@router.delete("/{id}", status_code=204)
def delete_media_type(id: int, session: Session = Depends(get_session)):
    """
    Delete a media type by its ID.
    """
    media_type = session.get(MediaType, id)
    if media_type:
        session.delete(media_type)
        session.commit()
    else:
        raise HTTPException(status_code=404)
