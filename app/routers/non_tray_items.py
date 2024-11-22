from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.non_tray_items import NonTrayItem
from app.models.barcodes import Barcode
from app.models.container_types import ContainerType
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.items import Item
from app.models.trays import Tray
from app.schemas.non_tray_items import (
    NonTrayItemInput,
    NonTrayItemMoveInput,
    NonTrayItemUpdateInput,
    NonTrayItemListOutput,
    NonTrayItemDetailWriteOutput,
    NonTrayItemDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
    BadRequest,
)
from app.tasks import manage_shelf_available_space

router = APIRouter(
    prefix="/non_tray_items",
    tags=["non tray items"],
)


@router.get("/", response_model=Page[NonTrayItemListOutput])
def get_non_tray_item_list(
    session: Session = Depends(get_session),
    owner_id: int = Query(default=None),
    size_class_id: int = Query(default=None),
    media_type_id: int = Query(default=None),
    from_dt: datetime = Query(default=None),
    to_dt: datetime = Query(default=None),
) -> list:
    """
    Get a paginated list of non tray items from the database
    """
    # Create a query to select all non tray items from the database
    query = select(NonTrayItem).distinct()

    if owner_id:
        query = query.where(NonTrayItem.owner_id == owner_id)
    if size_class_id:
        query = query.where(NonTrayItem.size_class_id == size_class_id)
    if media_type_id:
        query = query.where(NonTrayItem.media_type_id == media_type_id)
    if from_dt:
        query = query.where(NonTrayItem.accession_dt >= from_dt)
    if to_dt:
        query = query.where(NonTrayItem.accession_dt <= to_dt)

    return paginate(session, query)


@router.get("/{id}", response_model=NonTrayItemDetailReadOutput)
def get_non_tray_item_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a non_tray_item by its ID
    """
    non_tray_item = session.get(NonTrayItem, id)

    if non_tray_item:
        return non_tray_item

    raise NotFound(detail=f"Non Tray Item ID {id} Not Found")


@router.get("/barcode/{value}", response_model=NonTrayItemDetailReadOutput)
def get_non_tray_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a non-tray using a barcode value

    **Parameters:**
    - value (str): The value of the barcode to retrieve.
    """
    if not value:
        raise ValidationException(detail="Non Tray Item barcode value is required")

    statement = select(NonTrayItem).join(Barcode).where(Barcode.value == value)
    non_tray = session.exec(statement).first()
    if not non_tray:
        raise NotFound(detail=f"Non Tray Item barcode value {value} Not Found")
    return non_tray


@router.post("/", response_model=NonTrayItemDetailWriteOutput, status_code=201)
def create_non_tray_item(
    item_input: NonTrayItemInput, session: Session = Depends(get_session)
):
    """
    Create a new non_tray_item record
    """
    # check if barcode is already in use
    # check if item already exists with barcode
    item = session.query(Item).where(Item.barcode_id == item_input.barcode_id).first()
    non_tray_item = (
        session.query(NonTrayItem)
        .where(NonTrayItem.barcode_id == item_input.barcode_id)
        .first()
    )
    if item or non_tray_item:
        barcode = (
            session.query(Barcode).where(Barcode.id == item_input.barcode_id).first()
        )
        raise ValidationException(
            detail=f"Item " f"with barcode value" f" {barcode.value} already exists"
        )

    # Create a new non_tray_item
    new_non_tray_item = NonTrayItem(**item_input.model_dump())
    new_non_tray_item.withdrawal_dt = None
    # default to non-tray container_type
    container_type = (
        session.query(ContainerType).filter(ContainerType.type == "Non-Tray").first()
    )
    new_non_tray_item.container_type_id = container_type.id
    # non-trays are created in accession, set accession date
    if not new_non_tray_item.accession_dt:
        new_non_tray_item.accession_dt = datetime.utcnow()
    # check if existing withdrawn non-tray with this barcode
    previous_non_tray_item = session.exec(
        select(NonTrayItem).where(
            NonTrayItem.barcode_id == new_non_tray_item.barcode_id
        )
    ).first()
    if previous_non_tray_item:
        # use existing, and patch values
        for field, value in new_non_tray_item.model_dump(exclude={"id"}).items():
            setattr(previous_non_tray_item, field, value)
        new_non_tray_item = previous_non_tray_item
        new_non_tray_item.scanned_for_verification = False
        new_non_tray_item.scanned_for_shelving = False
        new_non_tray_item.scanned_for_refile_queue = False
        barcode = select(Barcode).where(Barcode.id == new_non_tray_item.barcode_id)
        barcode.withdrawn = False
        session.add(barcode)

    session.add(new_non_tray_item)
    session.commit()
    session.refresh(new_non_tray_item)

    return new_non_tray_item


@router.patch("/{id}", response_model=NonTrayItemDetailWriteOutput)
def update_non_tray_item(
    id: int,
    non_tray_item: NonTrayItemUpdateInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
):
    """
    Update a non_tray_item record in the database
    """
    # Get the existing non_tray_item record from the database
    existing_non_tray_item = session.get(NonTrayItem, id)

    # Check if the non_tray_item record exists
    if not existing_non_tray_item:
        raise NotFound(detail=f"Non Tray Item ID {id} Not Found")

    if non_tray_item.shelf_position_id is not None:
        new_shelf_position = (
            session.query(ShelfPosition)
            .filter(ShelfPosition.id == non_tray_item.shelf_position_id)
            .first()
        )

        if not new_shelf_position:
            raise NotFound(
                detail=f"Shelf Position ID {non_tray_item.shelf_position_id} Not Found"
            )

        shelf = (
            session.query(Shelf).filter(Shelf.id == new_shelf_position.shelf_id).first()
        )

        if not shelf:
            raise NotFound(detail=f"Shelf ID {new_shelf_position.shelf_id} Not Found")

        if shelf.available_space == 0:
            raise ValidationException(
                detail=f"Shelf id {shelf.id} has no available space"
            )

        if existing_non_tray_item.shelf_position_id is None:
            session.query(Shelf).filter(Shelf.id == shelf.id).update(
                {"available_space": shelf.available_space - 1}
            )

        if existing_non_tray_item.shelf_position_id and (
            non_tray_item.shelf_position_id != existing_non_tray_item.shelf_position_id
        ):
            existing_shelf_position = (
                session.query(ShelfPosition)
                .filter(ShelfPosition.id == existing_non_tray_item.shelf_position_id)
                .first()
            )

            if not existing_shelf_position:
                raise NotFound(
                    detail=f"Shelf Position ID {existing_non_tray_item.shelf_position_id} Not Found"
                )

            background_tasks.add_task(
                manage_shelf_available_space,
                session,
                existing_shelf_position,
                new_shelf_position,
            )

    # Update the non_tray_item record with the mutated data
    mutated_data = non_tray_item.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_non_tray_item, key, value)
    setattr(existing_non_tray_item, "update_dt", datetime.utcnow())

    # Commit the changes to the database
    session.add(existing_non_tray_item)
    session.commit()
    session.refresh(existing_non_tray_item)

    return existing_non_tray_item


@router.delete("/{id}")
def delete_non_tray_item(id: int, session: Session = Depends(get_session)):
    """
    Delete a non_tray_item by its ID
    """
    non_tray_item = session.get(NonTrayItem, id)

    if non_tray_item:
        if non_tray_item.shelf_position_id:
            shelf_position = session.query(ShelfPosition).get(
                non_tray_item.shelf_position_id
            )

            if shelf_position:
                shelf = session.query(Shelf).get(shelf_position.shelf_id)

                if shelf:
                    session.query(Shelf).filter(Shelf.id == shelf.id).update(
                        {"available_space": shelf.available_space + 1}
                    )

        session.delete(non_tray_item)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Non Tray Item ID {id} Deleted " f"Successfully"
        )

    raise NotFound(detail=f"Non Tray Item ID {id} Not Found")


@router.post("/move/{barcode_value}", response_model=NonTrayItemDetailReadOutput)
def move_item(
    barcode_value: str,
    non_tray_item_input: NonTrayItemMoveInput,
    session: Session = Depends(get_session),
):
    """
    Move a non_tray_item from one location to another.

    **Parameters:**
    - barcode_value: The value of the item to move.

    **Returns:**
    - Non Tray Item Detail Write Output: The updated non_tray_item details.
    """
    # Retrieve the non_tray_item and shelves in a single query
    query = (
        session.query(NonTrayItem, Shelf)
        .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id)
        .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
        .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
        .filter(Barcode.value == barcode_value)
    )
    result = query.first()
    if not result:
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} - Item with barcode not "
            f"found"
        )

    non_tray_item, source_shelf = result

    if (
        not non_tray_item.scanned_for_accession
        or not non_tray_item.scanned_for_verification
    ):
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} has not been verified."
        )

    # Retrieve the destination shelf
    destination_shelf = (
        session.query(Shelf)
        .join(Barcode, Shelf.barcode_id == Barcode.id)
        .filter(Barcode.value == non_tray_item_input.shelf_barcode_value)
        .first()
    )
    if not destination_shelf:
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} - Shelf with barcode value"
            f" {non_tray_item_input.shelf_barcode_value} not found"
        )

    # Check if the source and destination shelves are of the same size class
    if (
        source_shelf.shelf_type.size_class_id
        != destination_shelf.shelf_type.size_class_id
        or source_shelf.owner_id != destination_shelf.owner_id
    ):
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} - Shelf id"
            f" {destination_shelf.id} has no "
            f"available space"
        )

    # Check the available space in the destination shelf
    if destination_shelf.available_space < 1:
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} - Shelf id {destination_shelf.id} has no "
            f"available space"
        )

    # Check if the shelf position at destination shelf is unoccupied
    destination_shelf_positions = destination_shelf.shelf_positions
    destination_shelf_position_id = None
    for destination_shelf_position in destination_shelf_positions:
        shel_position_number = (
            session.query(ShelfPositionNumber)
            .filter(
                ShelfPositionNumber.id
                == destination_shelf_position.shelf_position_number_id
            )
            .first()
        )
        if shel_position_number.number == non_tray_item_input.shelf_position_number:
            destination_shelf_position_id = destination_shelf_position.id
            tray_shelf_position = (
                session.query(Tray)
                .filter(Tray.shelf_position_id == destination_shelf_position.id)
                .first()
            )
            non_tray_shelf_position = (
                session.query(NonTrayItem)
                .filter(NonTrayItem.shelf_position_id == destination_shelf_position.id)
                .first()
            )

            if tray_shelf_position or non_tray_shelf_position:
                raise ValidationException(
                    detail=f"Failed to transfer: {barcode_value} - Shelf Position"
                    f" {non_tray_item_input.shelf_position_number} is already occupied"
                )
            break

    # Update the non_tray_item and shelves
    non_tray_item.shelf_position_id = destination_shelf_position_id
    destination_shelf.available_space -= 1
    source_shelf.available_space += 1

    # Update the update_dt field
    update_dt = datetime.utcnow()
    non_tray_item.update_dt = update_dt
    source_shelf.update_dt = update_dt
    destination_shelf.update_dt = update_dt

    # Commit the changes
    session.add(non_tray_item)
    session.add(source_shelf)
    session.add(destination_shelf)
    session.commit()
    session.refresh(non_tray_item)
    session.refresh(source_shelf)
    session.refresh(destination_shelf)

    return non_tray_item
