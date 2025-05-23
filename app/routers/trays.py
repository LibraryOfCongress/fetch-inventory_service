from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime, timezone

from app.database.session import get_session, commit_record
from app.filter_params import SortParams, ItemFilterParams
from app.events import update_shelf_space_after_tray
from app.logger import inventory_logger
from app.models.move_discrepancies import MoveDiscrepancy
from app.models.non_tray_items import NonTrayItem
from app.models.owners import Owner
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.models.shelving_jobs import ShelvingJob
from app.models.size_class import SizeClass
from app.models.trays import Tray
from app.models.barcodes import Barcode
from app.models.container_types import ContainerType
from app.models.items import Item
from app.models.verification_changes import VerificationChange
from app.models.verification_jobs import VerificationJob
from app.schemas.trays import (
    TrayInput,
    TrayMoveInput,
    TrayUpdateInput,
    TrayListOutput,
    TrayDetailWriteOutput,
    TrayDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
)
from app.sorting import BaseSorter, ItemSorter

router = APIRouter(
    prefix="/trays",
    tags=["trays"],
)


@router.get("/", response_model=Page[TrayListOutput])
def get_tray_list(
    session: Session = Depends(get_session),
    params: ItemFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get a paginated list of trays from the database

    **Parameters:**
    - owner_id (int): The ID of the owner to filter by.
    - size_class_id (int): The ID of the size class to filter by.
    - media_type_id (int): The ID of the media type to filter by.
    - from_dt (datetime): The start date to filter by.
    - to_dt (datetime): The end date to filter by.
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - Tray List Output: The paginated list of trays.
    """
    # Create a query to select all trays from the database
    query = select(Tray)

    if params.barcode_value:
        barcode_value_subquery = select(Barcode.id).where(
            Barcode.value.in_(params.barcode_value)
        )
        query = query.where(Tray.barcode_id.in_(barcode_value_subquery))
    if params.owner_id:
        query = query.where(Tray.owner_id.in_(params.owner_id))
    if params.owner:
        owner_subquery = select(Owner.id).where(Owner.name.in_(params.owner))
        query = query.where(Tray.owner_id.in_(owner_subquery))
    if params.size_class_id:
        query = query.where(Tray.size_class_id.in_(params.size_class_id))
    if params.size_class:
        size_class_subquery = select(Tray.size_class_id).where(
            Tray.size_class.in_(params.size_class)
        )
        query = query.where(Tray.size_class_id.in_(size_class_subquery))
    if params.media_type_id:
        query = query.where(Tray.media_type_id.in_(params.media_type_id))
    if params.media_type:
        media_type_subquery = select(Tray.media_type_id).where(
            Tray.media_type.in_(params.media_type)
        )
        query = query.where(Tray.media_type_id.in_(media_type_subquery))
    if params.from_dt:
        query = query.where(Tray.accession_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(Tray.accession_dt <= params.to_dt)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = ItemSorter(Tray)
        query = sorter.apply_sorting(query, sort_params)

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

    tray = (
        session.query(Tray)
        .join(Barcode, Tray.barcode_id == Barcode.id)
        .filter(Barcode.value == value)
        .first()
    )
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
                detail=f"Tray with barcode {barcode.value} already exists"
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
        new_tray.accession_dt = datetime.now(timezone.utc)
    new_tray.container_type_id = container_type.id
    session.add(new_tray)
    session.commit()
    session.refresh(new_tray)

    update_shelf_space_after_tray(new_tray, None, None)

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

        if existing_tray.shelf_position_id and (
            tray.shelf_position_id != existing_tray.shelf_position_id
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

    # Checking if size class has changed
    if tray.size_class_id and tray.size_class_id != existing_tray.size_class_id:
        verification_job = session.get(VerificationJob, tray.verification_job_id)
        new_verification_changes = []
        tray_barcode = session.get(Barcode, tray.barcode_id)

        for item in existing_tray.items:
            session.query(Item).filter(Item.id == item.id).update(
                {
                    "size_class_id": tray.size_class_id,
                    "update_dt": datetime.now(timezone.utc),
                }
            )
            item_barcode = session.get(Barcode, item.barcode_id)
            new_verification_changes.append(
                VerificationChange(
                    workflow_id=verification_job.workflow_id,
                    tray_barcode_value=tray_barcode.value,
                    item_barcode_value=item_barcode.value,
                    change_type="SizeClassEdit",
                    completed_by_id=verification_job.user_id,
                )
            )
        session.add_all(new_verification_changes)

    # Checking if media type class has changed
    if tray.media_type_id and tray.media_type_id != existing_tray.media_type_id:
        verification_job = session.get(VerificationJob, tray.verification_job_id)
        new_verification_changes = []
        tray_barcode = session.get(Barcode, tray.barcode_id)
        for item in existing_tray.items:
            session.query(Item).filter(Item.id == item.id).update(
                {
                    "media_type_id": tray.media_type_id,
                    "update_dt": datetime.now(timezone.utc),
                }
            )
            item_barcode = session.get(Barcode, item.barcode_id)
            new_verification_changes.append(
                VerificationChange(
                    workflow_id=verification_job.workflow_id,
                    tray_barcode_value=tray_barcode.value,
                    item_barcode_value=item_barcode.value,
                    change_type="MediaTypeEdit",
                    completed_by_id=verification_job.user_id,
                )
            )
        session.add_all(new_verification_changes)

    # Update the tray record with the mutated data
    mutated_data = tray.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_tray, key, value)
    setattr(existing_tray, "update_dt", datetime.now(timezone.utc))

    # Commit the changes to the database
    session.add(existing_tray)
    session.commit()

    session.refresh(existing_tray)

    update_shelf_space_after_tray(
        existing_tray, existing_tray.shelf_position_id, tray.shelf_position_id
    )

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

        update_shelf_space_after_tray(None, None, tray.shelf_position_id)
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


@router.post("/move/{barcode_value}", response_model=TrayDetailReadOutput)
def move_tray(
    barcode_value: str,
    tray_input: TrayMoveInput,
    session: Session = Depends(get_session),
):
    """
    Move a tray from one location to another.

    **Parameters:**
    - barcode_value: The value of the tray to move.

    **Returns:**
    - Tray Detail Write Output: The updated tray details.
    """
    # Retrieve the non_tray_item and shelves in a single query
    tray = (
        session.query(Tray)
        .join(Barcode, Tray.barcode_id == Barcode.id)
        .filter(Barcode.value == barcode_value)
        .first()
    )
    if not tray:
        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Tray with barcode value not found"""
        )

        # Retrieve the non_tray_item and shelves in a single query
    src_shelf = (
        session.query(Shelf)
        .join(ShelfPosition, tray.shelf_position_id == ShelfPosition.id)
        .filter(ShelfPosition.shelf_id == Shelf.id)
        .first()
    )

    # Retrieve the destination shelf
    dest_shelf = (
        session.query(Shelf)
        .join(ShelfPosition, ShelfPosition.shelf_id == Shelf.id)
        .join(Barcode, Shelf.barcode_id == Barcode.id)
        .filter(Barcode.value == tray_input.shelf_barcode_value)
        .first()
    )

    current_assigned_location = None
    original_assigned_location = None
    if src_shelf:
        shelf_position = tray.shelf_position
        shelf_position_number = shelf_position.shelf_position_number
        original_assigned_location = (src_shelf.location + "-" + str(
            shelf_position_number.number))
    if dest_shelf:
        current_assigned_location = (dest_shelf.location + "-" + str(
            tray_input.shelf_position_number))

    if (
        not tray.scanned_for_accession or
        not tray.scanned_for_verification
    ):
        new_move_discrepancy = MoveDiscrepancy(
            tray_id=tray.id,
            assigned_user_id=tray_input.assigned_user_id,
            owner_id=tray.owner_id,
            size_class_id=tray.size_class_id,
            container_type_id=tray.container_type_id,
            original_assigned_location=original_assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Accessioned Discrepancy - Container barcode {barcode_value} has not been accessioned or verified""",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} has not been accessioned or verified"
        )

    if (
        tray.shelf_position_id is None or
        tray.withdrawn_barcode_id is not None or
        not src_shelf
    ):
        new_move_discrepancy = MoveDiscrepancy(
            tray_id=tray.id,
            assigned_user_id=tray_input.assigned_user_id,
            owner_id=tray.owner_id,
            size_class_id=tray.size_class_id,
            container_type_id=tray.container_type_id,
            original_assigned_location=original_assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Shelved Discrepancy - Container barcode {barcode_value} was not previously shelved""",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} - Container has not been assigned to a shelf position"
        )

    if not dest_shelf:
        new_move_discrepancy = MoveDiscrepancy(
            tray_id=tray.id,
            assigned_user_id=tray_input.assigned_user_id,
            owner_id=tray.owner_id,
            size_class_id=tray.size_class_id,
            container_type_id=tray.container_type_id,
            original_assigned_location=original_assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Shelved Discrepancy - Destination shelf with barcode {barcode_value} not found""",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Destination shelf with
            barcode value {tray_input.shelf_barcode_value} not found"""
        )

    # Check if the source and destination shelves are of the same size class
    if (
        src_shelf.shelf_type.size_class_id
        != dest_shelf.shelf_type.size_class_id
        or src_shelf.owner_id != dest_shelf.owner_id
    ):
        tray_size_class = (
            session.query(SizeClass).where(SizeClass.id == tray.size_class_id).first()
        )
        destination_size_class = (
            session.query(SizeClass)
            .where(SizeClass.id == dest_shelf.shelf_type.size_class_id)
            .first()
        )
        tray_owner = session.query(Owner).where(Owner.id == tray.owner_id).first()
        destination_owner = (
            session.query(Owner).where(Owner.id == dest_shelf.owner_id).first()
        )
        # Create a Discrepancy
        discrepancy_error = "Unknown"
        if (
            src_shelf.shelf_type.size_class_id
            != dest_shelf.shelf_type.size_class_id
        ):
            discrepancy_error = f"""Size Discrepancy - Container size class:
            {tray_size_class.name} does not match Shelf size class:
             {destination_size_class.name}"""
        if src_shelf.owner_id != dest_shelf.owner_id:
            discrepancy_error = f"""Owner Discrepancy - Container owner:
            {tray_owner.name} does not match Shelf owner: {destination_owner.name}"""

        new_move_discrepancy = MoveDiscrepancy(
            tray_id=tray.id,
            assigned_user_id=tray_input.assigned_user_id,
            owner_id=dest_shelf.owner_id,
            size_class_id=dest_shelf.shelf_type.size_class_id,
            container_type_id=tray.container_type_id,
            original_assigned_location=original_assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"{discrepancy_error}",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Shelf must be of the same size class and owner"""
        )

    # Check the available space in the destination shelf
    if dest_shelf.available_space < 1:
        new_move_discrepancy = MoveDiscrepancy(
            tray_id=tray.id,
            assigned_user_id=tray_input.assigned_user_id,
            owner_id=dest_shelf.owner_id,
            size_class_id=dest_shelf.shelf_type.size_class_id,
            container_type_id=tray.container_type_id,
            original_assigned_location=original_assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Available Space Discrepancy - Shelf {tray_input.shelf_barcode_value} has no available space""",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Shelf barcode {tray_input.shelf_barcode_value} at location {current_assigned_location} has no available space"""
        )

    destination_shelf_positions = dest_shelf.shelf_positions
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
        if shel_position_number.number == tray_input.shelf_position_number:
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
                new_move_discrepancy = MoveDiscrepancy(
                    tray_id=tray.id,
                    assigned_user_id=tray_input.assigned_user_id,
                    owner_id=dest_shelf.owner_id,
                    size_class_id=dest_shelf.shelf_type.size_class_id,
                    container_type_id=tray.container_type_id,
                    original_assigned_location=original_assigned_location,
                    current_assigned_location=current_assigned_location,
                    error=f"""Available Space Discrepancy - Shelf
                     Position {current_assigned_location} is already occupied""",
                )
                commit_record(session, new_move_discrepancy)
                raise ValidationException(
                    detail=f"""Failed to transfer: {barcode_value} - Shelf Position {current_assigned_location} is already occupied"""
                )
            break

    old_shelf_position_id = tray.shelf_position_id

    tray.shelf_position_id = destination_shelf_position_id

    # Update the update_dt field
    update_dt = datetime.now(timezone.utc)
    tray.update_dt = update_dt

    session.add(tray)
    session.commit()

    update_shelf_space_after_tray(
        tray, destination_shelf_position_id, old_shelf_position_id
    )

    return tray
