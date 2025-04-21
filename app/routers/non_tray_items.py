from io import StringIO

import pandas as pd
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime, timezone

from starlette.responses import StreamingResponse

from app.database.session import get_session, commit_record
from app.events import update_shelf_space_after_non_tray
from app.filter_params import SortParams
from app.logger import inventory_logger
from app.models.media_types import MediaType
from app.models.non_tray_items import NonTrayItem
from app.models.barcodes import Barcode
from app.models.container_types import ContainerType
from app.models.owners import Owner
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.items import Item
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.models.shelving_jobs import ShelvingJob
from app.models.size_class import SizeClass
from app.models.trays import Tray
from app.models.verification_changes import VerificationChange
from app.models.verification_jobs import VerificationJob
from app.filter_params import ItemFilterParams
from app.schemas.non_tray_items import (
    NonTrayItemInput,
    NonTrayItemMoveInput,
    NonTrayItemUpdateInput,
    NonTrayItemListOutput,
    NonTrayItemDetailWriteOutput,
    NonTrayItemDetailReadOutput,
)
from app.config.exceptions import NotFound, ValidationException
from app.sorting import ItemSorter

router = APIRouter(
    prefix="/non_tray_items",
    tags=["non tray items"],
)


@router.get("/", response_model=Page[NonTrayItemListOutput])
def get_non_tray_item_list(
    session: Session = Depends(get_session),
    params: ItemFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get a paginated list of non tray items from the database

    **Parameters:**
    - owner_id (int): The ID of the owner to filter by.
    - size_class_id (int): The ID of the size class to filter by.
    - media_type_id (int): The ID of the media type to filter by.
    - from_dt (datetime): The start date to filter by.
    - to_dt (datetime): The end date to filter by.
    - status (NonTrayItemStatus): The status to filter by.
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - Non Tray Item List Output: The paginated list of non tray items.
    """
    # Create a query to select all non tray items from the database
    query = select(NonTrayItem)

    if params.barcode_value:
        barcode_value_subquery = select(Barcode.id).where(
            Barcode.value.in_(params.barcode_value)
        )
        query = query.where(NonTrayItem.barcode_id.in_(barcode_value_subquery))
    if params.status:
        query = query.where(NonTrayItem.status.in_(params.status.value))
    if params.owner_id:
        query = query.where(NonTrayItem.owner_id.in_(params.owner_id))
    if params.owner:
        owner_subquery = select(Item.owner_id).where(Item.owner == params.owner)
        query = query.where(NonTrayItem.owner_id.in_(owner_subquery))
    if params.size_class_id:
        query = query.where(NonTrayItem.size_class_id.in_(params.size_class_id))
    if params.size_class:
        size_class_subquery = select(SizeClass.id).where(
            SizeClass.name.in_(params.size_class)
        )
        query = query.where(NonTrayItem.size_class_id.in_(size_class_subquery))
    if params.media_type_id:
        query = query.where(NonTrayItem.media_type_id.in_(params.media_type_id))
    if params.media_type:
        media_type_subquery = select(MediaType.id).where(
            MediaType.name.in_(params.media_type)
        )
        query = query.where(NonTrayItem.media_type_id.in_(media_type_subquery))
    if params.from_dt:
        query = query.where(NonTrayItem.accession_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(NonTrayItem.accession_dt <= params.to_dt)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = ItemSorter(NonTrayItem)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/download", response_class=StreamingResponse)
def download_non_tray_items(
    session: Session = Depends(get_session),
    params: ItemFilterParams = Depends(),
):
    """
    Get a paginated list of non tray items from the database

    **Parameters:**
    - owner_id (int): The ID of the owner to filter by.
    - size_class_id (int): The ID of the size class to filter by.
    - media_type_id (int): The ID of the media type to filter by.
    - from_dt (datetime): The start date to filter by.
    - to_dt (datetime): The end date to filter by.
    - status (NonTrayItemStatus): The status to filter by.

    **Returns:**
    - Non Tray Item List Output: The paginated list of non tray items.
    """
    # Create a query to select all non tray items from the database
    query = select(
        NonTrayItem.accession_dt,
        NonTrayItem.status,
        Owner.name.label("owner_name"),
        SizeClass.name.label("size_class_name"),
        MediaType.name.label("media_type_name"),
        Barcode.value.label("barcode_value"),
    ).join(NonTrayItem.owner).join(NonTrayItem.size_class).join(NonTrayItem.media_type).join(NonTrayItem.barcode)

    if params.barcode_value:
        query = query.where(Barcode.value.in_(params.barcode_value))
    if params.status:
        query = query.where(NonTrayItem.status.in_(params.status.value))
    if params.owner_id:
        query = query.where(NonTrayItem.owner_id.in_(params.owner_id))
    if params.owner:
        query = query.where(Owner.name.in_(params.owner))
    if params.size_class_id:
        query = query.where(NonTrayItem.size_class_id.in_(params.size_class_id))
    if params.size_class:
        query = query.where(SizeClass.name.in_(params.size_class))
    if params.media_type_id:
        query = query.where(NonTrayItem.media_type_id.in_(params.media_type_id))
    if params.media_type:
        query = query.where(MediaType.name.in_(params.media_type))
    if params.from_dt:
        query = query.where(NonTrayItem.accession_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(NonTrayItem.accession_dt <= params.to_dt)

    def generate_csv():
        output = StringIO()
        result = session.execute(query)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        df.to_csv(output, index=False)
        output.seek(0)
        yield output.read()

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; "
                                   "filename=items_advance_search.csv"
        },
    )

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

    non_tray = (
        session.query(NonTrayItem)
        .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
        .filter(Barcode.value == value)
        .first()
    )
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
            detail=f"Item with barcode value {barcode.value} already exists"
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
        new_non_tray_item.accession_dt = datetime.now(timezone.utc)
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

    update_shelf_space_after_non_tray(new_non_tray_item, None, None)

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
    inventory_logger.info(f"Updating Non Tray Items: {non_tray_item}")
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

    # Update the non_tray_item record with the mutated data
    mutated_data = non_tray_item.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        if (
            key in ["media_type_id", "size_class_id"]
            and existing_non_tray_item.__getattribute__(key) != value
            and existing_non_tray_item.verification_job_id
        ):
            verification_job = (
                session.query(VerificationJob)
                .filter(
                    VerificationJob.id == existing_non_tray_item.verification_job_id
                )
                .first()
            )
            non_tray_item_barcode = session.get(
                Barcode, existing_non_tray_item.barcode_id
            )

            new_verification_change = VerificationChange(
                workflow_id=verification_job.workflow_id,
                item_barcode_value=non_tray_item_barcode.value,
                change_type=(
                    "MediaTypeEdit" if key == "media_type_id" else "SizeClassEdit"
                ),
                completed_by_id=verification_job.user_id,
            )

            session.add(new_verification_change)

        setattr(existing_non_tray_item, key, value)
    setattr(existing_non_tray_item, "update_dt", datetime.now(timezone.utc))

    # Commit the changes to the database
    session.add(existing_non_tray_item)
    session.commit()
    session.refresh(existing_non_tray_item)

    update_shelf_space_after_non_tray(
        existing_non_tray_item,
        existing_non_tray_item.shelf_position_id,
        non_tray_item.shelf_position_id,
    )

    return existing_non_tray_item


@router.delete("/{id}")
def delete_non_tray_item(id: int, session: Session = Depends(get_session)):
    """
    Delete a non_tray_item by its ID
    """
    non_tray_item = session.get(NonTrayItem, id)

    if non_tray_item:
        update_shelf_space_after_non_tray(None, None, non_tray_item.shelf_position_id)
        session.delete(non_tray_item)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Non Tray Item ID {id} Deleted Successfully"
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
    non_tray_item = (
        session.query(NonTrayItem)
        .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
        .filter(Barcode.value == barcode_value)
        .first()
    )
    if not non_tray_item:
        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Non Tray Item with barcode value not found"""
        )

    source_shelf = (
        session.query(Shelf)
        .join(ShelfPosition, non_tray_item.shelf_position_id == ShelfPosition.id)
        .filter(ShelfPosition.shelf_id == Shelf.id)
        .first()
    )
    if not source_shelf:
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} - Shelf with barcode value not found"
        )

    if (
        non_tray_item.shelf_position_id is None
        or non_tray_item.status != "In"
        or non_tray_item.withdrawn_barcode_id is not None
    ):
        shelving_job_id = None
        assigned_user_id = None
        assigned_location = None

        if non_tray_item.shelving_job_id:
            # grab shelving job for user_id
            shelving_job = (
                session.query(ShelvingJob)
                .where(ShelvingJob.id == non_tray_item.shelving_job_id)
                .first()
            )
            shelving_job_id = shelving_job.id
            assigned_user_id = shelving_job.user_id

        pre_assigned_location = None
        if non_tray_item.shelf_position_proposed_id:
            pre_assigned_location = (
                session.query(ShelfPosition)
                .where(ShelfPosition.id == non_tray_item.shelf_position_proposed_id)
                .first()
            ).location

        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=shelving_job_id,
            non_tray_item_id=non_tray_item.id,
            assigned_user_id=assigned_user_id,
            owner_id=non_tray_item.owner_id,
            size_class_id=non_tray_item.size_class_id,
            pre_assigned_location=pre_assigned_location,
            assigned_location=assigned_location,
            error=f"""Not Shelved Discrepancy - Container barcode {barcode_value} is not in a Shelf""",
        )
        commit_record(session, new_shelving_job_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - has not been assigned to a shelf position"""
        )

    if (
        not non_tray_item.scanned_for_accession
        or not non_tray_item.scanned_for_verification
    ):
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} has not been verified"
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
            detail=f"""Failed to transfer: {barcode_value} - Shelf with barcode value {non_tray_item_input.shelf_barcode_value} not found"""
        )

    # Check if the source and destination shelves are of the same size class
    if (
        source_shelf.shelf_type.size_class_id
        != destination_shelf.shelf_type.size_class_id
        or source_shelf.owner_id != destination_shelf.owner_id
    ):
        non_tray_item_size_class = (
            session.query(SizeClass)
            .where(SizeClass.id == non_tray_item.size_class_id)
            .first()
        )
        destination_size_class = (
            session.query(SizeClass)
            .where(SizeClass.id == destination_shelf.shelf_type.size_class_id)
            .first()
        )
        non_tray_item_owner = (
            session.query(Owner).where(Owner.id == non_tray_item.owner_id).first()
        )
        destination_owner = (
            session.query(Owner).where(Owner.id == destination_shelf.owner_id).first()
        )
        # Create a Discrepancy
        discrepancy_error = "Unknown"
        if (
            source_shelf.shelf_type.size_class_id
            != destination_shelf.shelf_type.size_class_id
        ):
            discrepancy_error = f"""Size Discrepancy - Container size class: {non_tray_item_size_class.short_name} - Shelf size class: {destination_size_class.short_name}"""
        if source_shelf.owner_id != destination_shelf.owner_id:
            discrepancy_error = f"""Owner Discrepancy - Container owner: {non_tray_item_owner.name} - Shelf owner: {destination_owner.name}"""

        # grab shelving job for user_id
        shelving_job = (
            session.query(ShelvingJob)
            .where(ShelvingJob.id == non_tray_item.shelving_job_id)
            .first()
        )

        pre_assigned_location = None
        assigned_location = (
            session.query(ShelfPosition)
            .where(ShelfPosition.id == non_tray_item.shelf_position_id)
            .first()
        ).location

        if non_tray_item.shelf_position_proposed_id:
            pre_assigned_location = (
                session.query(ShelfPosition)
                .where(ShelfPosition.id == non_tray_item.shelf_position_proposed_id)
                .first()
            ).location

        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=shelving_job.id,
            non_tray_item_id=non_tray_item.id,
            assigned_user_id=shelving_job.user_id,
            owner_id=destination_shelf.owner_id,
            size_class_id=destination_shelf.shelf_type.size_class_id,
            assigned_location=assigned_location,
            pre_assigned_location=pre_assigned_location,
            error=f"{discrepancy_error}",
        )
        commit_record(session, new_shelving_job_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Shelf must be of the same size class and owner."""
        )
    # Check the available space in the destination shelf
    if destination_shelf.available_space < 1:
        # grab shelving job for user_id
        shelving_job = (
            session.query(ShelvingJob)
            .where(ShelvingJob.id == non_tray_item.shelving_job_id)
            .first()
        )
        pre_assigned_location = None
        assigned_location = (
            session.query(ShelfPosition)
            .where(ShelfPosition.id == non_tray_item.shelf_position_id)
            .first()
        ).location

        if non_tray_item.shelf_position_proposed_id:
            pre_assigned_location = (
                session.query(ShelfPosition)
                .where(ShelfPosition.id == non_tray_item.shelf_position_proposed_id)
                .first()
            ).location

        destination_shelf_barcode = (
            session.query(Barcode)
            .where(Barcode.id == destination_shelf.barcode_id)
            .first()
        )

        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=shelving_job.id,
            non_tray_item_id=non_tray_item.id,
            assigned_user_id=shelving_job.user_id,
            owner_id=destination_shelf.owner_id,
            size_class_id=destination_shelf.shelf_type.size_class_id,
            assigned_location=assigned_location,
            pre_assigned_location=pre_assigned_location,
            error=f"""Available Space Discrepancy - Shelf barcode: {destination_shelf_barcode.value} has no available space""",
        )
        commit_record(session, new_shelving_job_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Shelf barcode {destination_shelf_barcode.value} has no available space"""
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
                    detail=f"""Failed to transfer: {barcode_value} - Shelf Position {non_tray_item_input.shelf_position_number} is already occupied"""
                )
            break

    old_shelf_position_id = non_tray_item.shelf_position_id

    # Update the non_tray_item and shelves
    non_tray_item.shelf_position_id = destination_shelf_position_id

    # Update the update_dt field
    update_dt = datetime.now(timezone.utc)
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

    update_shelf_space_after_non_tray(
        non_tray_item, destination_shelf_position_id, old_shelf_position_id
    )

    return non_tray_item
