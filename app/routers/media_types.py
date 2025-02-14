from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime, timezone
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
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
from app.utilities import get_sorted_query

router = APIRouter(
    prefix="/media-types",
    tags=["media types"],
)


@router.get("/", response_model=Page[MediaTypeListOutput])
def get_media_type_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a list of media types

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - Media Type List Output: A list of media types.
    """
    # Create a query to retrieve all Media Type
    query = select(MediaType).distinct()

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(MediaType, query, sort_params)

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



@router.post("/", response_model=MediaTypeDetailWriteOutput, status_code=201)
def create_media_type(
    media_type_input: MediaTypeInput, session: Session = Depends(get_session)
):
    """
    Create a new media type record.

    **type**: Required varchar 25
    """
    try:
        new_media_type = MediaType(**media_type_input.model_dump())

        session.add(new_media_type)
        session.commit()
        session.refresh(new_media_type)

        return new_media_type

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=MediaTypeDetailWriteOutput)
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

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_media_type(id: int, session: Session = Depends(get_session)):
    """
    Delete a media type by its ID.
    """
    media_type = session.get(MediaType, id)

    if media_type:
        session.delete(media_type)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Media Type ID {id} Deleted "
                                    f"Successfully"
        )

    raise NotFound(detail=f"Media Type ID {id} Not Found")
