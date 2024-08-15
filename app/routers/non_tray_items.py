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
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.schemas.non_tray_items import (
    NonTrayItemInput,
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

    try:
        # Create a new non_tray_item
        new_non_tray_item = NonTrayItem(**item_input.model_dump())
        new_non_tray_item.withdrawal_dt = None
        # default to non-tray container_type
        container_type = (
            session.query(ContainerType)
            .filter(ContainerType.type == "Non-Tray")
            .first()
        )
        new_non_tray_item.container_type_id = container_type.id
        # non-trays are created in accession, set accession date
        if not new_non_tray_item.accession_dt:
            new_non_tray_item.accession_dt = datetime.utcnow()
        # check if existing withdrawn non-tray with this barcode
        previous_non_tray_item = session.exec(select(NonTrayItem).where(
            NonTrayItem.barcode_id == new_non_tray_item.barcode_id
        )).first()
        if previous_non_tray_item:
            # use existing, and patch values
            for field, value in new_non_tray_item.dict(exclude={'id'}).items():
                setattr(previous_non_tray_item, field, value)
            new_non_tray_item = previous_non_tray_item
            new_non_tray_item.scanned_for_verification = False
            new_non_tray_item.scanned_for_shelving = False
            new_non_tray_item.scanned_for_refile_queue = False

        session.add(new_non_tray_item)
        session.commit()
        session.refresh(new_non_tray_item)

        return new_non_tray_item

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


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

    if (
        non_tray_item.shelf_position_id
        and non_tray_item.shelf_position_id
        != existing_non_tray_item.shelf_position_id
    ):
        existing_non_tray_item_shelf_position = (
            session.query(NonTrayItem)
            .filter(
                NonTrayItem.shelf_position_id == non_tray_item.shelf_position_id
            )
            .first()
        )

        if existing_non_tray_item_shelf_position:
            raise ValidationException(
                detail=f"Non Tray Item already exists at "
                f"shelf position {non_tray_item.shelf_position_id}"
            )

        shelf_position = (
            session.query(ShelfPosition)
            .filter(ShelfPosition.id == non_tray_item.shelf_position_id)
            .first()
        )

        if not shelf_position:
            raise NotFound(
                detail=f"Shelf Position ID {non_tray_item.shelf_position_id} Not Found"
            )

        shelf = session.query(Shelf).filter(
            Shelf.id == shelf_position.shelf_id
        ).first()

        if not shelf:
            raise NotFound(detail=f"Shelf ID {shelf_position.shelf_id} Not Found")

        background_tasks.add_task(
            manage_shelf_available_space, session, shelf, existing_non_tray_item_shelf_position
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
        session.delete(non_tray_item)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Non Tray Item ID {id} Deleted " f"Successfully"
        )

    raise NotFound(detail=f"Non Tray Item ID {id} Not Found")
