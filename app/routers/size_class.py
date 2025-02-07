from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime

from app.config.exceptions import BadRequest, InternalServerError
from app.database.session import get_session
from app.filter_params import SortParams
from app.logger import inventory_logger
from app.models.size_class import SizeClass
from app.schemas.size_class import (
    SizeClassInput,
    SizeClassUpdateInput,
    SizeClassListOutput,
    SizeClassDetailWriteOutput,
    SizeClassDetailReadOutput,
)
from app.utilities import get_sorted_query

router = APIRouter(
    prefix="/size_class",
    tags=["size class"],
)


@router.get("/", response_model=Page[SizeClassListOutput])
def get_size_class_list(
    session: Session = Depends(get_session),
    short_name: str | None = None,
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a paginated list of size classes

    **Parameters:**
    - short_name (str): The short name of the size class to filter by.
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - Size Class List Output: The paginated list of size classes
    """
    # Create a query to select all sides from the database
    query = select(SizeClass).distinct()

    if short_name:
        query = query.where(SizeClass.short_name == short_name)

        if query is None:
            raise HTTPException(status_code=404, detail="Size class not found")

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(SizeClass, query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=SizeClassDetailReadOutput)
def get_size_class_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a size class by its ID.
    """
    size_class = session.get(SizeClass, id)
    if size_class:
        return size_class
    else:
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/", response_model=SizeClassDetailWriteOutput, status_code=201)
def create_size_class(
    size_class_input: SizeClassInput, session: Session = Depends(get_session)
):
    """
    Create a new size class record.
    """

    new_size_class = SizeClass(**size_class_input.model_dump())
    session.add(new_size_class)
    session.commit()
    session.refresh(new_size_class)

    return new_size_class


@router.patch("/{id}", response_model=SizeClassDetailWriteOutput)
def update_size_class(
    id: int,
    size_class_input: SizeClassUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a size class record in the database
    """
    # Get the existing size_class record from the database
    existing_size_class = session.get(SizeClass, id)

    # Check if the size_class record exists
    if not existing_size_class:
        raise HTTPException(status_code=404, detail="Not Found")

    # Update the size_class record with the mutated data
    mutated_data = size_class_input.model_dump(
        exclude_unset=True
    )

    for key, value in mutated_data.items():
        setattr(existing_size_class, key, value)
    setattr(existing_size_class, "update_dt", datetime.utcnow())

    # Commit the changes to the database
    session.add(existing_size_class)
    session.commit()
    session.refresh(existing_size_class)

    return existing_size_class


@router.delete("/{id}")
def delete_size_class(id: int, session: Session = Depends(get_session)):
    """
    Delete a size_class by its ID
    """
    size_class = session.get(SizeClass, id)

    if size_class:
        session.delete(size_class)
        session.commit()
        return HTTPException(status_code=204)
    else:
        raise HTTPException(status_code=404, detail=f"Size Class ID {id} Not Found")
