import csv
from io import StringIO

import pandas as pd
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime, timezone

from starlette.responses import StreamingResponse

from app.database.session import get_session, commit_record
from app.events import update_shelf_space_after_tray
from app.filter_params import SortParams, ItemFilterParams
from app.logger import inventory_logger
from app.models.barcodes import Barcode
from app.models.items import Item
from app.models.media_types import MediaType
from app.models.move_discrepancies import MoveDiscrepancy
from app.models.non_tray_items import NonTrayItem
from app.models.owners import Owner
from app.models.shelf_positions import ShelfPosition
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.models.shelving_jobs import ShelvingJob
from app.models.size_class import SizeClass
from app.models.trays import Tray
from app.models.verification_changes import VerificationChange
from app.models.verification_jobs import VerificationJob
from app.schemas.items import (
    ItemInput,
    ItemMoveInput,
    ItemUpdateInput,
    ItemListOutput,
    ItemDetailWriteOutput,
    ItemDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import ItemSorter
from app.tasks import process_tray_item_move

router = APIRouter(
    prefix="/items",
    tags=["items"],
)


@router.get("/", response_model=Page[ItemListOutput])
def get_item_list(
    session: Session = Depends(get_session),
    params: ItemFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Retrieve a paginated list of items from the database.

    **Parameters:**
    - owner_id (int): The ID of the owner to filter by.
    - size_class_id (int): The ID of the size class to filter by.
    - media_type_id (int): The ID of the media type to filter by.
    - from_dt (datetime): The start date to filter by.
    - to_dt (datetime): The end date to filter by.
    - status (ItemStatus): The status to filter by.
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - Item List Output: The paginated list of items.
    """
    # Create a query to select all items from the database
    item_queryset = select(Item)

    if params.status:
        item_queryset = item_queryset.where(Item.status.in_(params.status))
    if params.owner_id:
        item_queryset = item_queryset.where(Item.owner_id.in_(params.owner_id))
    if params.owner:
        owner_subquery = select(Owner.id).where(Owner.name.in_(params.owner)).distinct()
        item_queryset = item_queryset.where(Item.owner_id.in_(owner_subquery))
    if params.size_class_id:
        item_queryset = item_queryset.where(
            Item.size_class_id.in_(params.size_class_id)
        )
    if params.size_class:
        size_class_subquery = (
            select(SizeClass.id).where(SizeClass.name.in_(params.size_class)).distinct()
        )
        item_queryset = item_queryset.where(Item.size_class_id.in_(size_class_subquery))
    if params.media_type_id:
        item_queryset = item_queryset.where(
            Item.media_type_id.in_(params.media_type_id)
        )
    if params.media_type:
        media_type_subquery = (
            select(MediaType.id).where(MediaType.name.in_(params.media_type)).distinct()
        )
        item_queryset = item_queryset.where(Item.media_type_id.in_(media_type_subquery))
    if params.barcode_value:
        barcode_value_subquery = (
            select(Barcode.id).where(Barcode.value.in_(params.barcode_value)).distinct()
        )
        item_queryset = item_queryset.where(Item.barcode_id.in_(barcode_value_subquery))
    if params.from_dt:
        item_queryset = item_queryset.where(Item.accession_dt >= params.from_dt)
    if params.to_dt:
        item_queryset = item_queryset.where(Item.accession_dt <= params.to_dt)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = ItemSorter(Item)
        item_queryset = sorter.apply_sorting(item_queryset, sort_params)

    return paginate(session, item_queryset)


@router.get("/download", response_class=StreamingResponse)
def download_items(
    session: Session = Depends(get_session),
    params: ItemFilterParams = Depends(),
):
    """
       Retrieve a paginated list of items from the database.

       **Parameters:**
       - owner_id (int): The ID of the owner to filter by.
       - size_class_id (int): The ID of the size class to filter by.
       - media_type_id (int): The ID of the media type to filter by.
       - from_dt (datetime): The start date to filter by.
       - to_dt (datetime): The end date to filter by.
       - status (ItemStatus): The status to filter by.
       - sort_params (SortParams): The sorting parameters.

       **Returns:**
       - Item List Output: The paginated list of items.
       """
    # Create a query to select all items from the database

    item_queryset = (
        select(
            Item.accession_dt,
            Item.status,
            Owner.name.label("owner_name"),
            SizeClass.name.label("size_class_name"),
            MediaType.name.label("media_type_name"),
            Barcode.value.label("barcode_value"),
        )
        .outerjoin(Owner, Item.owner_id == Owner.id)
        .outerjoin(SizeClass, Item.size_class_id == SizeClass.id)
        .outerjoin(MediaType, Item.media_type_id == MediaType.id)
        .outerjoin(Barcode, Item.barcode_id == Barcode.id)
    )

    if params.barcode_value:
        item_queryset = item_queryset.where(Barcode.value.in_(params.barcode_value))
    if params.status:
        item_queryset = item_queryset.where(Item.status.in_(params.status))
    if params.owner_id:
        item_queryset = item_queryset.where(Item.owner_id.in_(params.owner_id))
    if params.owner:
        item_queryset = item_queryset.where(Owner.name.in_(params.owner))
    if params.size_class_id:
        item_queryset = item_queryset.where(
            Item.size_class_id.in_(params.size_class_id)
        )
    if params.size_class:
        if params.size_class:
            item_queryset = item_queryset.where(SizeClass.name.in_(params.size_class))
    if params.media_type_id:
        item_queryset = item_queryset.where(
            Item.media_type_id.in_(params.media_type_id)
        )
    if params.media_type:
        item_queryset = item_queryset.where(MediaType.name.in_(params.media_type))
    if params.from_dt:
        item_queryset = item_queryset.where(Item.accession_dt >= params.from_dt)
    if params.to_dt:
        item_queryset = item_queryset.where(Item.accession_dt <= params.to_dt)

    def generate_csv():
        output = StringIO()
        result = session.execute(item_queryset)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        df.to_csv(output, index=False)
        output.seek(0)
        yield output.read()

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; "
                                        "filename=items_advance_search.csv"},
    )


@router.get("/{id}", response_model=ItemDetailReadOutput)
def get_item_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve details of a specific item by ID.

    **Args:**
    - id (int): The ID of the item to retrieve.

    **Returns:**
    - Item Detail Read Output: Details of the item.

    **Raises:**
    - HTTPException: If the item is not found.
    """
    item = session.get(Item, id)
    if item:
        return item

    raise NotFound(detail=f"Item ID {id} Not Found")


@router.get("/barcode/{value}", response_model=ItemDetailReadOutput)
def get_item_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a item using a barcode value

    **Parameters:**
    - value (str): The value of the barcode to retrieve.
    """
    if not value:
        raise ValidationException(detail="Item barcode value is required")
    item = (
        session.query(Item)
        .join(Barcode, Item.barcode_id == Barcode.id)
        .filter(Barcode.value == value)
        .first()
    )
    if not item:
        raise NotFound(detail=f"Item with barcode value {value} not found")
    return item


@router.post("/", response_model=ItemDetailWriteOutput, status_code=201)
def create_item(item_input: ItemInput, session: Session = Depends(get_session)):
    """
    Create a new item in the database.

    **Parameters:**
    - Item Input: model containing item details to be added.

    **Returns:**
    - Item Detail Write Output: Newly created item details.
    """
    # check if barcode is already in use
    # check if non tray item already exists with barcode
    non_tray_item = (
        session.query(NonTrayItem)
        .filter(NonTrayItem.barcode_id == item_input.barcode_id)
        .first()
    )
    item = session.query(Item).filter(Item.barcode_id == item_input.barcode_id).first()
    if non_tray_item or item:
        barcode = (
            session.query(Barcode).where(Barcode.id == item_input.barcode_id).first()
        )
        raise ValidationException(
            detail=f"Item with barcode value {barcode.value} already exists"
        )

    # Create a new item
    new_item = Item(**item_input.model_dump())
    new_item.withdrawal_dt = None
    # accession is how items are created. Set accession_dt
    if not new_item.accession_dt:
        new_item.accession_dt = datetime.now(timezone.utc)

    # check if existing withdrawn item with this barcode
    previous_item = session.exec(
        select(Item).where(Item.barcode_id == new_item.barcode_id)
    ).first()
    if previous_item:
        # use existing, and patch values
        for field, value in new_item.dict(exclude={"id"}).items():
            setattr(previous_item, field, value)
        new_item = previous_item
        new_item.scanned_for_verification = False
        new_item.scanned_for_refile_queue = False
        barcode = select(Barcode).where(Barcode.id == new_item.barcode_id)
        barcode.withdrawn = False
        session.add(barcode)
    session.add(new_item)
    session.commit()
    session.refresh(new_item)

    return new_item


@router.patch("/{id}", response_model=ItemDetailWriteOutput)
def update_item(
    id: int, item: ItemUpdateInput, session: Session = Depends(get_session)
):
    """
    Update item details in the database.

    **Args:**
    - id: The ID of the item to update.
    - Item Update Input: The updated item data.

    **Returns:**
    - Item Detail Write Output: The updated item details.
    """
    try:
        # Get the existing item record from the database
        existing_item = session.get(Item, id)

        # Check if the item record exists
        if not existing_item:
            raise NotFound(detail=f"Item ID {id} Not Found")

        # Update the item record with the mutated data
        mutated_data = item.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            if (
                key in ["media_type_id", "size_class_id"]
                and existing_item.__getattribute__(key) != value
                and existing_item.verification_job_id
            ):
                verification_job = (
                    session.query(VerificationJob)
                    .filter(VerificationJob.id == existing_item.verification_job_id)
                    .first()
                )
                tray_barcode = (
                    session.query(Barcode)
                    .join(Tray, Barcode.id == Tray.barcode_id)
                    .filter(Tray.id == item.tray_id)
                    .first()
                )
                item_barcode = session.get(Barcode, existing_item.barcode_id)

                new_verification_change = VerificationChange(
                    workflow_id=verification_job.workflow_id,
                    tray_barcode_value=tray_barcode.value,
                    item_barcode_value=item_barcode.value,
                    change_type=(
                        "MediaTypeEdit" if key == "media_type_id" else "SizeClassEdit"
                    ),
                    completed_by_id=verification_job.user_id,
                )

                session.add(new_verification_change)

            setattr(existing_item, key, value)
        setattr(existing_item, "update_dt", datetime.now(timezone.utc))

        # Commit the changes to the database
        session.add(existing_item)
        session.commit()
        session.refresh(existing_item)

        return existing_item

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_item(id: int, session: Session = Depends(get_session)):
    """
    Delete an item by its ID.

    **Parameters:**
    - id: the ID of the item to be deleted

    **Returns:**
    - HTTPException: status code 204 if item is successfully deleted, status code 404 if item not found
    """

    item = session.get(Item, id)

    if item:
        session.delete(item)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Item ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Item ID {id} Not Found")


@router.post("/move/{barcode_value}", response_model=ItemDetailReadOutput)
def move_item(
    barcode_value: str,
    item_input: ItemMoveInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
):
    """
    Move an item from one location to another.

    **Parameters:**
    - barcode_value: The value of the item to move.

    **Returns:**
    - Item Detail Write Output: The updated item details.
    """
    item_lookup_barcode_value = (
        session.query(Barcode).where(Barcode.value == barcode_value).first()
    )
    if not item_lookup_barcode_value:
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} Item with barcode not found"
        )
    tray_look_barcode_value = (
        session.query(Barcode)
        .where(Barcode.value == item_input.tray_barcode_value)
        .first()
    )

    if not tray_look_barcode_value:
        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Tray barcode value {item_input.tray_barcode_value} not found"""
        )

    item = (
        session.query(Item)
        .filter(Item.barcode_id == item_lookup_barcode_value.id)
        .first()
    )

    if not item:
        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Item barcode value {item_lookup_barcode_value.value} not found"""
        )

    src_tray = session.query(Tray).filter(Tray.id == item.tray_id).first()
    dest_tray = session.query(Tray).filter(Tray.barcode_id == tray_look_barcode_value.id).first()
    current_assigned_location = (
        session.query(ShelfPosition).filter(
            ShelfPosition.id == dest_tray.shelf_position_id
        ).first()
    ).location
    assigned_location = None
    if src_tray and src_tray.shelf_position_id:
        assigned_location = (
            session.query(ShelfPosition).filter(
                ShelfPosition.id == src_tray.shelf_position_id
            ).first()
        ).location

    if not src_tray:
        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Tray Item not found"""
        )

    if not item.scanned_for_accession or not item.scanned_for_verification:
        new_move_discrepancy = MoveDiscrepancy(
            item_id=item.id,
            tray_id=item.tray_id,
            assigned_user_id=item_input.assigned_user_id,
            owner_id=item.owner_id,
            size_class_id=item.size_class_id,
            container_type_id=src_tray.container_type_id,
            original_assigned_location=assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Accessioned Discrepancy - Tray Item barcode
                    {barcode_value} has not been accessioned or verified""",
        )
        commit_record(session, new_move_discrepancy)
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} has not been accessioned or verified"
        )

    if (
        src_tray.shelf_position_id is None or
        src_tray.withdrawn_barcode_id is not None
    ):
        new_move_discrepancy = MoveDiscrepancy(
            item_id=item.id,
            tray_id=item.tray_id,
            assigned_user_id=item_input.assigned_user_id,
            owner_id=item.owner_id,
            size_class_id=item.size_class_id,
            container_type_id=src_tray.container_type_id,
            original_assigned_location=assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Shelved Discrepancy - Tray Item barcode
            {barcode_value} was not previously shelved""",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Tray Item was not previously shelved"""
        )

    if not dest_tray:
        new_move_discrepancy = MoveDiscrepancy(
            item_id=item.id,
            tray_id=item.tray_id,
            assigned_user_id=item_input.assigned_user_id,
            owner_id=item.owner_id,
            size_class_id=item.size_class_id,
            container_type_id=src_tray.container_type_id,
            original_assigned_location=assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Shelved Discrepancy - Destination Container barcode
             {item_input.tray_barcode_value} not found""",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Container barcode {item_input.tray_barcode_value} not found"""
        )

    if (
        dest_tray.shelf_position_id is None or
        dest_tray.withdrawn_barcode_id is not None
    ):
        new_move_discrepancy = MoveDiscrepancy(
            item_id=item.id,
            tray_id=item.tray_id,
            assigned_user_id=item_input.assigned_user_id,
            owner_id=item.owner_id,
            size_class_id=item.size_class_id,
            container_type_id=src_tray.container_type_id,
            original_assigned_location=assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Shelved Discrepancy - Scanned Container barcode
             {item_input.tray_barcode_value} was not previously shelved""",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Scanned Container barcode {item_input.tray_barcode_value} was not previously shelved"""
        )

    if (
        item.status != "In"
        or item.withdrawn_barcode_id is not None
        or item.tray_id is None
    ):
        new_move_discrepancy = MoveDiscrepancy(
            item_id=item.id,
            tray_id=item.tray_id,
            assigned_user_id=item_input.assigned_user_id,
            owner_id=item.owner_id,
            size_class_id=item.size_class_id,
            container_type_id=src_tray.container_type_id,
            original_assigned_location=assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Shelved Discrepancy - Item barcode {barcode_value} is not in a tray""",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: Item barcode {barcode_value} is not in a tray"""
        )

    background_tasks.add_task(
        process_tray_item_move(session, item, src_tray, dest_tray)
    )

    return item
