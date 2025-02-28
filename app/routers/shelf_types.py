from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.shelf_types import ShelfType
from app.models.shelves import Shelf
from app.models.size_class import SizeClass
from app.schemas.shelf_types import (
    ShelfTypeInput,
    ShelfTypeUpdateInput,
    ShelfTypeListOutput,
    ShelfTypeDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    MethodNotAllowed,
    ValidationException,
    InternalServerError,
    BadRequest,
)
from app.sorting import BaseSorter

router = APIRouter(
    prefix="/shelf-types",
    tags=["shelf types"],
)


@router.get("/", response_model=Page[ShelfTypeListOutput])
def get_shelf_type_list(
    session: Session = Depends(get_session),
    size_class_id: int = None,
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a paginated list of Shelf Types.

    **Parameters:**
    - size_class_id (int): The ID of the size class to filter by.
    - sort_params (SortParams): The sorting parameters.

    **Returns**:
    - Shelf Type List Output: The paginated list of shelf type.
    """

    # Create a query to select all Shelf Position Number
    query = select(ShelfType).distinct()

    if size_class_id:
        query = query.where(ShelfType.size_class_id == size_class_id)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(ShelfType)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=ShelfTypeDetailOutput)
def get_shelf_type_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a Shelf Type from the database using the provided ID.

    **Args**:
    - id: The ID of the shelf type.

    **Returns**:
    - Shelf Type Detail Read Output: The details of the shelf type.

    **Raises**:
    - HTTPException: If the shelf type is not found in the database.
    """
    if not id:
        raise BadRequest(detail="Shelf Type ID Required")

    # Retrieve the aisle from the database using the provided ID
    shelf_type = session.get(ShelfType, id)

    if shelf_type:
        return shelf_type

    raise NotFound(detail=f"Shelf Type ID {id} Not Found")


@router.post("/", response_model=ShelfTypeDetailOutput)
def create_shelf_type(
    shelf_type_input: ShelfTypeInput, session: Session = Depends(get_session)
):
    """
    Create a new Shelf Type.

    **Args**:
    - Shelf Type Input: The input data for creating a new shelf type.

    **Returns**:
    - Shelf Type Detail Output: The created shelf type.

    **Raises**:
    - HTTPException: If there is an integrity error when adding the new shelf type to
    the database.
    """
    try:
        # Create a new Shelf Type object
        new_shelf_type = ShelfType(**shelf_type_input.model_dump())
        session.add(new_shelf_type)
        session.commit()
        session.refresh(new_shelf_type)

        return new_shelf_type

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=ShelfTypeDetailOutput)
def update_shelf_type(
    id: int,
    shelf_type_input: ShelfTypeUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update an existing Shelf Type in the database.

    **Args**:
    - id: The ID of the shelf type to update.
    - Shelf Type Update Input: The input data for updating the shelf type.

    **Returns**:
    - Shelf Type Detail Output: The updated shelf type.

    **Raises**:
    - HTTPException: If the shelf type with the given ID does not exist in the database.
    """

    try:
        if not id:
            raise BadRequest(detail="Shelf Type ID Required")

        # Check if shelf_type has associated child shelves
        existing_shelf_type = session.exec(select(ShelfType).where(ShelfType.id == id)).one_or_none()

        if not existing_shelf_type:
            raise NotFound(detail=f"Shelf Type ID {id} Not Found")

        mutated_data = shelf_type_input.model_dump(exclude_unset=True)

        if 'max_capacity' in mutated_data.keys():
        # Check if the parent has associated children
        # Below method avoids having to load for check
            child_shelves_count = session.exec(
                select(func.count(Shelf.id)).where(Shelf.shelf_type_id == id)
            ).one()
            if child_shelves_count > 0:
                # deny decrement
                if mutated_data["max_capacity"] < existing_shelf_type.max_capacity:
                    shelf_type_size_class = session.exec(select(SizeClass).where(
                        SizeClass.id == existing_shelf_type.size_class_id
                    )).one_or_none()
                    raise MethodNotAllowed(
                        detail=f"""Cannot decrease capacity of Shelf Type id {id} ({shelf_type_size_class.short_name} {existing_shelf_type.type}), it is in use by {child_shelves_count} shelves"""
                    )

        for key, value in mutated_data.items():
            setattr(existing_shelf_type, key, value)

        setattr(existing_shelf_type, "update_dt", datetime.now(timezone.utc))

        session.add(existing_shelf_type)
        session.commit()
        session.refresh(existing_shelf_type)

        return existing_shelf_type

    except Exception as e:
        if isinstance(e, MethodNotAllowed):
            raise e

        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_shelf_type(id: int, session: Session = Depends(get_session)):
    """
    Delete a Shelf Type by its ID.

    **Args**:
    - id: The ID of the shelf type to delete.

    **Raises**:
    - HTTPException: If the shelf type with the given ID does not exist.

    **Returns**:
    - None
    """
    if not id:
        raise BadRequest(detail="Shelf Type ID Required")

    shelf_type = session.get(ShelfType, id)

    if shelf_type:
        child_shelves_count = session.exec(
            select(func.count(Shelf.id)).where(Shelf.shelf_type_id == id)
        ).one()
        if child_shelves_count > 0:
            shelf_type_size_class = session.exec(select(SizeClass).where(
                SizeClass.id == shelf_type.size_class_id
            )).one_or_none()
            raise MethodNotAllowed(
                detail=f"""Cannot delete Shelf Type id {id} ({shelf_type_size_class.short_name} {shelf_type.type}), it is in use by {child_shelves_count} shelves"""
            )
        else:
            session.delete(shelf_type)
            session.commit()

        return HTTPException(
            status_code=204, detail=f"Shelf Type ID {id} Deleted " f"Successfully"
        )

    raise NotFound(detail=f"Shelf Type ID {id} Not Found")
