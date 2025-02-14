from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime, timezone
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.schemas.shelf_positions import (
    ShelfPositionInput,
    ShelfPositionUpdateInput,
    ShelfPositionListOutput,
    ShelfPositionDetailReadOutput,
    ShelfPositionDetailWriteOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.utilities import get_sorted_query

router = APIRouter(
    prefix="/shelves/positions",
    tags=["shelves"],
)


@router.get("/", response_model=Page[ShelfPositionListOutput])
def get_shelf_position_list(
    session: Session = Depends(get_session),
    shelf_id: int | None = None,
    empty: bool | None = False,
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a list of shelf positions.

    **Parameters:**
    - shelf_id (int): The ID of the shelf to filter by.
    - empty (bool): Whether to filter by empty shelf positions.
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - Shelf Position List Output: The paginated list of shelf positions.
    """
    if shelf_id and empty:
        statement = (
            select(ShelfPosition)
            .where(ShelfPosition.shelf_id == shelf_id)
            .where(ShelfPosition.tray == None)
            .where(ShelfPosition.non_tray_item == None)
        )
    elif shelf_id:
        statement = select(ShelfPosition).where(ShelfPosition.shelf_id == shelf_id)
    elif empty:
        statement = (
            select(ShelfPosition)
            .where(ShelfPosition.tray == None)
            .where(ShelfPosition.non_tray_item == None)
        )
    else:
        statement = select(ShelfPosition)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        statement = get_sorted_query(ShelfPosition, statement, sort_params)

    return paginate(session, statement)


@router.get("/{id}", response_model=ShelfPositionDetailReadOutput)
def get_shelf_position_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve a shelf position detail by its ID.

    **Parameters:**
    - id: The ID of the shelf position.

    **Returns:**
    - Shelf Position Detail Read Output: The shelf position detail.

    **Raises:**
    - HTTPException: If the shelf position is not found.
    """
    shelf_position = session.get(ShelfPosition, id)

    if shelf_position:
        return shelf_position

    raise NotFound(detail=f"Shelf Position ID {id} Not Found")


@router.post("/", response_model=ShelfPositionDetailWriteOutput, status_code=201)
def create_shelf_position(
    shelf_position_input: ShelfPositionInput,
    session: Session = Depends(get_session),
) -> ShelfPosition:
    """
    Create a new shelf position.

    **Args:**
    - Shelf Position Input: Input data for creating a shelf position.

    **Returns:**
    - Shelf Position: The newly created shelf position.

    **Raises:**
    - HTTPException: If there is an integrity error when adding the shelf position to
    the database.
    """
    shelf = session.query(Shelf).get(shelf_position_input.shelf_id)
    shelf_type = shelf.shelf_type
    shelf_position_number = session.query(ShelfPositionNumber).get(
        shelf_position_input.shelf_position_number_id
    )
    if not shelf:
        raise NotFound(detail=f"Shelf ID {shelf_position_input.shelf_id} Not Found")

    if not shelf_position_number:
        raise NotFound(
            detail=f"Shelf Position Number ID {shelf_position_input.shelf_position_number_id} Not Found"
        )

    shelf_position = shelf_position_number.number

    if len(shelf.shelf_positions) >= shelf_type.max_capacity:
        raise ValidationException(
            detail=f"Shelf Position {shelf_position} for Shelf ID"
            f" {shelf.id} exceeds "
            f"max capacity of {shelf_type.max_capacity}"
        )

    new_shelf_position = ShelfPosition(**shelf_position_input.model_dump())

    session.add(shelf)
    session.add(new_shelf_position)
    session.commit()
    session.refresh(new_shelf_position)

    return new_shelf_position


@router.patch("/{id}", response_model=ShelfPositionDetailWriteOutput)
def update_shelf_position(
    id: int,
    shelf_position: ShelfPositionUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a shelf position with the given ID.

    **Args:**
    - id: The ID of the shelf position to update.
    - Shelf Position Update Input: The updated shelf position data.

    **Raises:**
    - HTTPException: If the shelf position with the given ID does not exist or if
    there is an internal server error.

    **Returns:**
    - Shelf Position Detail WriteOutput: The updated shelf position.
    """
    try:
        existing_shelf_position = session.get(ShelfPosition, id)

        if existing_shelf_position is None:
            raise NotFound(detail=f"Shelf Position ID {id} Not Found")

        shelf = session.get(Shelf, existing_shelf_position.shelf_id)

        if not shelf:
            raise NotFound(
                detail=f"Shelf ID {existing_shelf_position.shelf_id} Not Found"
            )

        shelf_position_number = session.get(
            ShelfPositionNumber, existing_shelf_position.shelf_position_number_id
        )

        if not shelf_position_number:
            raise NotFound(
                detail=f"Shelf Position Number ID {existing_shelf_position.shelf_position_number_id} Not Found"
            )

        mutated_data = shelf_position.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_shelf_position, key, value)

        setattr(existing_shelf_position, "update_dt", datetime.now(timezone.utc))
        session.add(existing_shelf_position)
        session.commit()
        session.refresh(existing_shelf_position)

        return existing_shelf_position

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_shelf_position(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelf position by its ID.

    **Args:**
    - id: The ID of the shelf position to delete.

    **Raises:**
    - HTTPException: If the shelf position does not exist.

    **Returns:**
    - None
    """
    shelf_position = session.get(ShelfPosition, id)
    if not shelf_position:
        raise NotFound(detail=f"Shelf Position ID {id} Not Found")

    if shelf_position:
        if shelf_position.tray or shelf_position.non_tray_item:
            raise ValidationException(
                detail="Can not delete shelf position associated tray and non-tray items"
            )

    session.delete(shelf_position)
    session.commit()

    return HTTPException(
        status_code=204, detail=f"Shelf Position ID {id} Deleted Successfully"
    )
