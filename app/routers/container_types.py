from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Response, Query
from sqlmodel import Session, select
from datetime import datetime, timezone
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
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

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.
    - search (Optional[str]): The search query.
        - Type: The type of the container type.

    **Returns:**
    - Container Type List Output: A list of container types.
    """

    # Create a query to retrieve all Container Type
    query = select(ContainerType)

    if search:
        query = query.where(ContainerType.type.contains(search))

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

    **Args:**
    - id: The ID of the container type to retrieve.

    **Returns:**
    - Container Type Detail Read Output: The details of the container type.

    **Raises:**
    - HTTPException: If the container type with the specified ID is not found.
    """
    container_type = session.get(ContainerType, id)
    if container_type:
        return container_type

    raise NotFound(detail=f"Container Type ID {id} Not Found")


@router.post("/", response_model=ContainerTypeDetailWriteOutput, status_code=201)
def create_container_type(
    container_type_input: ContainerTypeInput, session: Session = Depends(get_session)
):
    """
    Create a new container type record.'

    **Args:**
    - Container Type Input: The input data for the new container type.

    **Returns:**
    - Container Type: The newly created container type.

    **type**: Required varchar 25
    """
    try:
        new_container_type = ContainerType(**container_type_input.model_dump())

        session.add(new_container_type)
        session.commit()
        session.refresh(new_container_type)

        return new_container_type

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=ContainerTypeDetailWriteOutput)
def update_container_type(
    id: int, container_type: ContainerTypeInput, session: Session = Depends(get_session)
):
    """
    Update an existing container type in the database.

    **Parameters:**
    - id: The id of the container type to update.
    - Container Type Input: The updated container type data.

    **Returns:**
    - Container Type Detail Write Output: The updated container type.
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

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_container_type(id: int, session: Session = Depends(get_session)):
    """
    Deletes a container type from the database by its ID.

    **Args:**
    - id: The ID of the container type to delete.

    **Raises:**
    - HTTPException: If the container type with the given ID is not found.
    """
    container_type = session.get(ContainerType, id)

    if container_type:
        session.delete(container_type)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Container Type ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Container Type ID {id} Not Found")
