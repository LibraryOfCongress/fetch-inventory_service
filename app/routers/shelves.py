import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.logger import inventory_logger
from app.models.shelf_types import ShelfType
from app.models.shelves import Shelf
from app.models.barcodes import Barcode
from app.models.shelf_numbers import ShelfNumber
from app.models.buildings import Building
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.ladders import Ladder
from app.schemas.shelves import (
    ShelfInput,
    ShelfUpdateInput,
    ShelfListOutput,
    ShelfDetailWriteOutput,
    ShelfDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

router = APIRouter(
    prefix="/shelves",
    tags=["shelves"],
)

LOGGER = logging.getLogger("app.routers.shelves")


@router.get("/", response_model=Page[ShelfListOutput])
def get_shelf_list(
    session: Session = Depends(get_session),
    building_id: int | None = None,
    module_id: int | None = None,
    aisle_id: int | None = None,
    side_id: int | None = None,
    ladder_id: int | None = None,
    shelf_id: int | None = None,
    owner_id: int | None = None,
    size_class_id: int | None = None,
    unassigned: bool | None = None
) -> list:
    """
    Get a list of shelves.

    **Returns:**
    - Shelf List Output: The paginated list of shelves.
    """
    shelf_queryset = select(Shelf).distinct()

    if owner_id:
        shelf_queryset = shelf_queryset.where(Shelf.owner_id == owner_id)

    if size_class_id:
        shelf_queryset = shelf_queryset.join(
            ShelfType, Shelf.shelf_type_id == ShelfType.id
        ).where(
            ShelfType.size_class_id == size_class_id
        )

    # location from most to least constrained
    if shelf_id:
        shelf_queryset = shelf_queryset.where(Shelf.id == shelf_id)
    elif ladder_id:
        shelf_queryset = shelf_queryset.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).where(
            Ladder.id == ladder_id
        )
    elif side_id:
        shelf_queryset = shelf_queryset.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).where(
            Side.id == side_id
        )
    elif aisle_id:
        shelf_queryset = shelf_queryset.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).join(
            Aisle, Side.aisle_id == Aisle.id
        ).where(
            Aisle.id == aisle_id
        )
    elif module_id:
        shelf_queryset = shelf_queryset.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).join(
            Aisle, Side.aisle_id == Aisle.id
        ).join(
            Module, Aisle.module_id == Module.id
        ).where(
            Module.id == module_id
        )
    elif building_id:
        shelf_queryset = shelf_queryset.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).join(
            Aisle, Side.aisle_id == Aisle.id
        ).join(
            Module, Aisle.module_id == Module.id
        ).join(
            Building, Module.building_id == Building.id
        ).where(
            Building.id == building_id
        )

    if unassigned:
        shelf_queryset = shelf_queryset.where(Shelf.barcode_id == None)

    return paginate(session, shelf_queryset)


@router.get("/{id}", response_model=ShelfDetailReadOutput)
def get_shelf_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a shelf with the given ID.

    **Args:**
    - id: The ID of the shelf to retrieve.

    **Returns:**
    - Shelf Detail Read Output: The details of the retrieved shelf.

    **Raises:**
    - HTTPException: If the shelf with the specified ID is not found.
    """
    shelf = session.get(Shelf, id)

    if shelf:
        return shelf

    raise NotFound(detail=f"Shelf ID {id} Not Found")


@router.get("/barcode/{value}", response_model=ShelfDetailReadOutput)
def get_shelf_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a shelf using a barcode value

    **Parameters:**
    - value (str): The value of the barcode to retrieve.
    """
    statement = select(Shelf).join(Barcode).where(Barcode.value == value)
    shelf = session.exec(statement).first()
    if not shelf:
        raise NotFound(detail=f"Shelf with barcode value {value} not found")
    return shelf


@router.post("/", response_model=ShelfDetailWriteOutput, status_code=201)
def create_shelf(
    shelf_input: ShelfInput, session: Session = Depends(get_session)
) -> Shelf:
    """
    Create a shelf:

    **Args:**
    - Shelf Input: The input data for creating the shelf.

    **Returns:**
    - Shelf Detail Write Output: The newly created shelf.

    **Notes:**
    - **ladder_id**: Required integer id for parent ladder
    - **container_type_id**: Required integer id for related container type
    - **shelf_number_id**: Required integer id for related shelf number
    - **barcode_id**: Optional uuid for related barcode
    - **height**: Required numeric (scale 4, precision 2) height in inches
    - **width**: Required numeric (scale 4, precision 2) width in inches
    - **depth**: Required numeric (scale 4, precision 2) depth in inches
    """
    # Check if shelf # or shelf_number_id
    shelf_number = shelf_input.shelf_number
    shelf_number_id = shelf_input.shelf_number_id
    mutated_data = shelf_input.model_dump(exclude="shelf_number")

    if not shelf_number_id and not shelf_number:
        raise ValidationException(detail=f"shelf_number_id OR shelf_number required")
    elif shelf_number and not shelf_number_id:
        # get shelf_number_id from shelf number
        shelf_num_object = (
            session.query(ShelfNumber)
            .filter(ShelfNumber.number == shelf_number)
            .first()
        )
        if not shelf_num_object:
            raise ValidationException(
                detail=f"No shelf_number entity exists for shelf number {shelf_number}"
            )
        mutated_data["shelf_number_id"] = shelf_num_object.id

    # new_shelf = Shelf(**shelf_input.model_dump())
    new_shelf = Shelf(**mutated_data)
    session.add(new_shelf)
    session.commit()
    session.refresh(new_shelf)

    return new_shelf


@router.patch("/{id}", response_model=ShelfDetailWriteOutput)
def update_shelf(
    id: int, shelf_input: ShelfUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a shelf with the given ID.

    **Args:**
    - id: The ID of the shelf to update.
    - Shelf Update Input: The updated shelf data.

    **Raises:**
    - HTTPException: If the shelf with the given ID does not exist or if there is a
    server error.

    **Returns:**
    - Shelf Detail Write Output: The updated shelf.
    """
    existing_shelf = session.get(Shelf, id)

    if existing_shelf is None:
        raise NotFound(detail=f"Shelf ID {id} Not Found")

    mutated_data = shelf_input.model_dump(exclude_unset=True)

    if shelf_input.available_space:
        shelf_positions_count = len(existing_shelf.shelf_positions)
        if shelf_positions_count == 0:
            raise ValidationException(
                detail=f"The are no shelf position assigned to shelf"
            )
        elif (
            shelf_positions_count > 0
            and shelf_input.available_space > shelf_positions_count
        ):
            raise ValidationException(
                detail=f"The available space can exceed the number of shelf positions"
            )

    for key, value in mutated_data.items():
        setattr(existing_shelf, key, value)

    setattr(existing_shelf, "update_dt", datetime.utcnow())
    session.add(existing_shelf)
    session.commit()
    session.refresh(existing_shelf)

    return existing_shelf


@router.delete("/{id}")
def delete_shelf(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelf by its ID.

    **Args:**
    - id: The ID of the shelf to delete.

    **Raises:**
    - HTTPException: If the shelf with the given id is not found.

    **Returns:**
    - None
    """
    shelf = session.get(Shelf, id)

    if shelf:
        session.delete(shelf)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Shelf ID {id} Deleted " f"Successfully"
        )

    raise NotFound(detail=f"Shelf ID {id} Not Found")
