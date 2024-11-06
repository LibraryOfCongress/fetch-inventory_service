from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.shelf_types import ShelfType
from app.models.shelves import Shelf
from app.schemas.shelf_types import (
    ShelfTypeInput,
    ShelfTypeUpdateInput,
    ShelfTypeListOutput,
    ShelfTypeDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
    BadRequest,
)


router = APIRouter(
    prefix="/shelf-types",
    tags=["shelf types"],
)


@router.get("/", response_model=Page[ShelfTypeListOutput])
def get_shelf_type_list(
    size_class_id: int = None, session: Session = Depends(get_session)
) -> list:
    """
    Get a paginated list of Shelf Types.

    **Returns**:
    - Shelf Type List Output: The paginated list of shelf type.
    """

    if size_class_id:
        return paginate(
            session, select(ShelfType).where(ShelfType.size_class_id == size_class_id)
        )

    return paginate(session, select(ShelfType))


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
    id: int, shelf_type: ShelfTypeUpdateInput, session: Session = Depends(get_session)
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

        existing_shelf_type = session.get(ShelfType, id)

        if not existing_shelf_type:
            raise NotFound(detail=f"Shelf Type ID {id} Not Found")

        # Check shelf capacity
        if shelf_type.max_capacity and existing_shelf_type.max_capacity is not None:
            if shelf_type.max_capacity < 1:
                raise ValidationException(
                    detail="Shelf capacity may not be less than one."
                )

            if shelf_type.max_capacity < existing_shelf_type.max_capacity:
                existing_shelves = (
                    session.query(Shelf).filter(Shelf.shelf_type_id == id)
                ).all()

                for shelf in existing_shelves:
                    if (
                        existing_shelf_type.max_capacity - shelf_type.max_capacity
                    ) > shelf.available_space:
                        raise ValidationException(
                            detail="Capacity cannot be reduced below "
                            f"currently shelved {shelf.id} containers for "
                            f"Shelf ID {shelf.id}."
                        )

                for shelf in existing_shelves:
                    if len(shelf.shelf_positions) == 0:
                        session.query(Shelf).filter(Shelf.id == shelf.id).update(
                            {"available_space": shelf_type.max_capacity}
                        )
                    elif len(shelf.shelf_positions) > 0:
                        if (
                            len(shelf.shelf_positions) + shelf.available_space
                        ) < shelf_type.max_capacity:
                            session.query(Shelf).filter(Shelf.id == shelf.id).update(
                                {"available_space": shelf_type.max_capacity}
                            )

        mutated_data = shelf_type.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_shelf_type, key, value)

        setattr(existing_shelf_type, "update_dt", datetime.utcnow())

        session.add(existing_shelf_type)
        session.commit()
        session.refresh(existing_shelf_type)

        return existing_shelf_type

    except Exception as e:
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
        session.delete(shelf_type)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Shelf Type ID {id} Deleted " f"Successfully"
        )

    raise NotFound(detail=f"Shelf Type ID {id} Not Found")
