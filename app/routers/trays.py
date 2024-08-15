from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.trays import Tray
from app.models.barcodes import Barcode
from app.models.container_types import ContainerType
from app.models.items import Item
from app.schemas.trays import (
    TrayInput,
    TrayUpdateInput,
    TrayListOutput,
    TrayDetailWriteOutput,
    TrayDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.tasks import manage_shelf_available_space


router = APIRouter(
    prefix="/trays",
    tags=["trays"],
)


@router.get("/", response_model=Page[TrayListOutput])
def get_tray_list(
    session: Session = Depends(get_session),
    owner_id: int = Query(default=None),
    size_class_id: int = Query(default=None),
    media_type_id: int = Query(default=None),
    barcode_value: str = Query(default=None),
    from_dt: datetime = Query(default=None),
    to_dt: datetime = Query(default=None),
) -> list:
    """
    Get a paginated list of trays from the database
    """
    # Create a query to select all trays from the database
    query = select(Tray).distinct()

    if barcode_value:
        query = query.join(Barcode, Tray.barcode_id == Barcode.id)
        query = query.where(Barcode.value == barcode_value)
    if owner_id:
        query = query.where(Tray.owner_id == owner_id)
    if size_class_id:
        query = query.where(Tray.size_class_id == size_class_id)
    if media_type_id:
        query = query.where(Tray.media_type_id == media_type_id)
    if from_dt:
        query = query.where(Tray.accession_dt >= from_dt)
    if to_dt:
        query = query.where(Tray.accession_dt <= to_dt)

    return paginate(session, query)


@router.get("/{id}", response_model=TrayDetailReadOutput)
def get_tray_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a tray by its ID
    """
    tray = session.get(Tray, id)

    if tray:
        return tray

    raise NotFound(detail=f"Tray ID {id} Not Found")


@router.get("/barcode/{value}", response_model=TrayDetailReadOutput)
def get_tray_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a tray using a barcode value

    **Parameters:**
    - value (str): The value of the barcode to retrieve.
    """
    if not value:
        raise ValidationException(detail="Tray barcode value is required")

    statement = select(Tray).join(Barcode).where(Barcode.value == value)
    tray = session.exec(statement).first()
    if not tray:
        raise NotFound(detail=f"Tray barcode value {value} not found")
    return tray


@router.post("/", response_model=TrayDetailWriteOutput, status_code=201)
def create_tray(tray_input: TrayInput, session: Session = Depends(get_session)):
    """
    Create a new tray record
    """
    # Check if a tray with the same barcode already exists
    if tray_input.barcode_id:
        existing_tray = (
            session.query(Tray).filter(Tray.barcode_id == tray_input.barcode_id).first()
        )

        if existing_tray:
            barcode = existing_tray.barcode
            raise ValidationException(
                detail=f"Tray with barcode {barcode.value} " f"already exists"
            )

    # Create a new tray
    new_tray = Tray(**tray_input.model_dump())
    new_tray.withdrawal_dt = None

    # default to tray container_type
    container_type = (
        session.query(ContainerType).filter(ContainerType.type == "Tray").first()
    )
    # trays are created at accession, set accession date
    if not new_tray.accession_dt:
        new_tray.accession_dt = datetime.utcnow()
    new_tray.container_type_id = container_type.id
    session.add(new_tray)
    session.commit()
    session.refresh(new_tray)

    return new_tray


@router.patch("/{id}", response_model=TrayDetailWriteOutput)
def update_tray(
    id: int,
    tray: TrayUpdateInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
):
    """
    Update a tray record in the database
    """
    # Get the existing tray record from the database
    existing_tray = session.get(Tray, id)

    # Check if the tray record exists
    if not existing_tray:
        raise NotFound(detail=f"Tray ID {id} Not Found")

    if tray.shelf_position_id is not None:
        new_shelf_position = (
            session.query(ShelfPosition)
            .filter(ShelfPosition.id == tray.shelf_position_id)
            .first()
        )

        if not new_shelf_position:
            raise NotFound(
                detail=f"Shelf Position ID {tray.shelf_position_id} Not Found"
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

        if existing_tray.shelf_position_id is None:
            session.query(Shelf).filter(Shelf.id == shelf.id).update(
                {"available_space": shelf.available_space - 1}
            )

        if (
            existing_tray.shelf_position_id
            and tray.shelf_position_id != existing_tray.shelf_position_id
        ):
            # Check if a tray already exists at the new shelf position
            existing_tray_shelf_position = (
                session.query(Tray)
                .filter(Tray.shelf_position_id == tray.shelf_position_id)
                .first()
            )

            if existing_tray_shelf_position:
                raise ValidationException(
                    detail=f"Tray already exists at shelf position {tray.shelf_position_id}"
                )

            existing_shelf_position = (
                session.query(ShelfPosition)
                .filter(ShelfPosition.id == existing_tray.shelf_position_id)
                .first()
            )

            if not existing_shelf_position:
                raise NotFound(
                    detail=f"Shelf Position ID {existing_tray.shelf_position_id} Not Found"
                )

            background_tasks.add_task(
                manage_shelf_available_space,
                session,
                existing_shelf_position,
                new_shelf_position,
            )

    # Update the tray record with the mutated data
    mutated_data = tray.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_tray, key, value)
    setattr(existing_tray, "update_dt", datetime.utcnow())

    # Commit the changes to the database
    session.add(existing_tray)
    session.commit()
    session.refresh(existing_tray)

    return existing_tray


@router.delete("/{id}")
def delete_tray(id: int, session: Session = Depends(get_session)):
    """
    Delete a tray by its ID
    """
    tray = session.get(Tray, id)

    if tray:
        items_to_delete = session.exec(
            select(Item).where(Item.tray_id == id).distinct()
        )
        for item in items_to_delete:
            session.delete(item)
            session.commit()
        session.delete(tray)
        session.commit()
        for item in items_to_delete:
            session.delete(session.get(Barcode, item.barcode_id))
            session.commit()
        session.delete(session.get(Barcode, tray.barcode_id))
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Tray id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Tray ID {id} Not Found")
