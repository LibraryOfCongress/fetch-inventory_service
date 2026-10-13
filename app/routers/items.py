# /code/app/routers/items.py - REFACRORED TO SQLALCHEMY V2

import csv
import re
from datetime import datetime, timezone
from typing import Optional, List
from io import StringIO
import pandas as pd

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, update, func # select/update imported from sqlalchemy now
from starlette.responses import StreamingResponse

from app.database.session import get_session, commit_record
from app.events import update_shelf_space_after_tray
from app.filter_params import SortParams, ItemFilterParams
from app.logger import inventory_logger
from app.models.barcodes import Barcode
from app.models.items import Item, ItemStatus, ILSSyncState
from app.models.accession_jobs import AccessionJob
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
    BadRequest,
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import ItemSorter
from app.tasks import process_tray_item_move
from app.ils.interfaces import ILSItemMetadata
from app.models.ils_configurations import ILSConfiguration
from app.ils.factory import get_ils_adapter

from app.auth.dependencies import RequiresPermission
from app.services.audit_service import log_audit_event, AuditEventType

router = APIRouter(
    prefix="/items",
    tags=["items"],
)


@router.get("/", response_model=Page[ItemListOutput], dependencies=[Depends(RequiresPermission("can_access_item_detail"))])
def get_item_list(
    session: Session = Depends(get_session),
    params: ItemFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Retrieve a paginated list of items from the database.
    """
    # Create a query to select all items from the database
    item_queryset = select(Item)

    if params.status:
        item_queryset = item_queryset.where(Item.status.in_(params.status))
    if params.owner_id:
        item_queryset = item_queryset.where(Item.owner_id.in_(params.owner_id))
    if params.owner:
        owner_subquery = select(Owner.id).where(Owner.name.in_(params.owner)).distinct().scalar_subquery()
        item_queryset = item_queryset.where(Item.owner_id.in_(owner_subquery))
    if params.size_class_id:
        item_queryset = item_queryset.where(
            Item.size_class_id.in_(params.size_class_id)
        )
    if params.size_class:
        size_class_subquery = (
            select(SizeClass.id).where(SizeClass.name.in_(params.size_class)).distinct().scalar_subquery()
        )
        item_queryset = item_queryset.where(Item.size_class_id.in_(size_class_subquery))
    if params.media_type_id:
        item_queryset = item_queryset.where(
            Item.media_type_id.in_(params.media_type_id)
        )
    if params.media_type:
        media_type_subquery = (
            select(MediaType.id).where(MediaType.name.in_(params.media_type)).distinct().scalar_subquery()
        )
        item_queryset = item_queryset.where(Item.media_type_id.in_(media_type_subquery))
    if params.barcode_value:
        barcode_value_subquery = (
            select(Barcode.id).where(Barcode.value.in_(params.barcode_value)).distinct().scalar_subquery()
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

    # CRITICAL FIX: Paginate needs both session and query for SQLAlchemy 2.0
    return paginate(session, item_queryset)


@router.get("/download", response_class=StreamingResponse, dependencies=[Depends(RequiresPermission("can_access_item_detail"))])
def download_items(
    session: Session = Depends(get_session),
    params: ItemFilterParams = Depends(),
):
    """
       Retrieve a paginated list of items from the database.
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
        # V2 FIX: session.execute(query) returns a Result object
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


@router.get("/{id}", response_model=ItemDetailReadOutput, dependencies=[Depends(RequiresPermission("can_access_item_detail"))])
def get_item_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve details of a specific item by ID.
    """
    item = session.get(Item, id)
    if item:
        return item

    raise NotFound(detail=f"Item ID {id} Not Found")


@router.get("/barcode/{value}", response_model=ItemDetailReadOutput, dependencies=[Depends(RequiresPermission("can_access_item_detail"))])
def get_item_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a item using a barcode value
    """
    if not value:
        raise ValidationException(detail="Item barcode value is required")
    # V2 FIX: session.query().join().filter().first() -> session.execute(select(...)).scalars().first()
    item = (
        session.execute(
            select(Item)
            .join(Barcode, Item.barcode_id == Barcode.id)
            .filter(Barcode.value == value)
        )
        .scalars()
        .first()
    )
    if not item:
        raise NotFound(detail=f"Item with barcode value {value} not found")
    return item


@router.get("/barcode/{value}/metadata", response_model=ILSItemMetadata, dependencies=[Depends(RequiresPermission("can_access_item_detail"))])
def get_item_metadata_by_barcode(value: str, session: Session = Depends(get_session)):
    """
    [JIT METADATA LOOKUP]
    Retrieve temporary, read-only bibliographic details from the ILS.
    """
    if not value:
        raise ValidationException(detail="Item barcode value is required")
        
    barcode_obj = session.execute(
        select(Barcode).where(Barcode.value == value)
    ).scalars().first()
    
    if not barcode_obj:
        raise NotFound(detail=f"Barcode value {value} not found")
        
    item = session.execute(select(Item).filter(Item.barcode_id == barcode_obj.id)).scalars().first()
    non_tray_item = session.execute(select(NonTrayItem).filter(NonTrayItem.barcode_id == barcode_obj.id)).scalars().first()
    
    target = item or non_tray_item
    if not target or not target.owner_id:
        raise NotFound(detail="Cannot determine owner for item metadata lookup.")
        
    owner = session.get(Owner, target.owner_id)
    if not owner or not owner.resolved_ils_configuration_id:
        raise ValidationException(detail="No active ILS integration configured for this item's owner (or it is disabled).")
        
    config = session.get(ILSConfiguration, owner.resolved_ils_configuration_id)
    if not config or not config.is_active or not config.enable_jit_metadata_hook:
        raise ValidationException(detail="JIT Metadata lookups are disabled or inactive for this item's ILS configuration.")
        
    try:
        adapter = get_ils_adapter(config)
        return adapter.fetch_item_metadata(value)
    except HTTPException:
        raise
    except Exception as e:
        inventory_logger.error(f"Failed to fetch JIT metadata for {value}: {e}")
        raise InternalServerError(detail="ILS Synchronization currently unreachable or mapping failed.")


@router.post("/", response_model=ItemDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_access_accession"))])
def create_item(
    item_input: ItemInput, 
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None
):
    """
    Create a new item in the database.
    """
    # check if barcode is already in use
    # V2 FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
    non_tray_item = (
        session.execute(select(NonTrayItem).filter(NonTrayItem.barcode_id == item_input.barcode_id))
        .scalars()
        .first()
    )
    # V2 FIX
    item = session.execute(select(Item).filter(Item.barcode_id == item_input.barcode_id)).scalars().first()
    
    if non_tray_item or item:
        # V2 FIX
        barcode = (
            session.execute(select(Barcode).where(Barcode.id == item_input.barcode_id))
            .scalars()
            .first()
        )
        raise ValidationException(
            detail=f"Item with barcode value {barcode.value} already exists"
        )
    # --- SYNCHRONOUS ILS VALIDATION FOR VERIFICATION JOBS ---
    ils_sync_state = None
    if item_input.verification_job_id:
        verification_job = session.get(VerificationJob, item_input.verification_job_id)
        if verification_job:
            owner_id = verification_job.owner_id
            if not owner_id and verification_job.accession_job_id:
                accession_job = session.get(AccessionJob, verification_job.accession_job_id)
                owner_id = accession_job.owner_id if accession_job else None
            
            if owner_id:
                owner = session.get(Owner, owner_id)
                if owner and owner.resolved_ils_configuration_id:
                    config = session.get(ILSConfiguration, owner.resolved_ils_configuration_id)
                    if config and config.is_active and config.enable_accession_hook:
                        adapter = get_ils_adapter(config)
                        barcode_obj = session.get(Barcode, item_input.barcode_id)
                        if barcode_obj:
                            is_valid = adapter.validate_item(barcode_obj.value)
                            if not is_valid:
                                raise ValidationException(detail=f"ILS Validation Failed: Barcode {barcode_obj.value} is invalid or not mapped to this location.")
                            else:
                                ils_sync_state = ILSSyncState.IN_SYNC

    # Create a new item
    new_item = Item(**item_input.model_dump())
    new_item.withdrawal_dt = None
    # accession is how items are created. Set accession_dt
    if not new_item.accession_dt:
        new_item.accession_dt = datetime.now(timezone.utc)
    
    # Set default status to Accessioned for new items
    new_item.status = ItemStatus.Accessioned

    if ils_sync_state:
        new_item.ils_sync_state = ils_sync_state

    # check if existing withdrawn item with this barcode
    # Query by withdrawn_barcode_id since withdrawn items have barcode_id = None
    previous_item = session.execute(
        select(Item).where(Item.withdrawn_barcode_id == new_item.barcode_id)
    ).scalars().first()
    
    if previous_item:
        # Reuse the existing withdrawn item record
        # Restore barcode relationship
        previous_item.barcode_id = new_item.barcode_id
        previous_item.withdrawn_barcode_id = None
        
        # Clear withdrawal tracking fields
        previous_item.withdrawal_dt = None
        previous_item.withdrawn_location = None
        previous_item.withdrawn_internal_location = None
        previous_item.withdrawn_loc_bcodes = None
        
        # Update with new accession data
        previous_item.accession_dt = datetime.now(timezone.utc)
        previous_item.accession_job_id = new_item.accession_job_id
        previous_item.owner_id = new_item.owner_id
        previous_item.size_class_id = new_item.size_class_id
        previous_item.media_type_id = new_item.media_type_id
        previous_item.subcollection_id = new_item.subcollection_id
        previous_item.title = new_item.title
        previous_item.volume = new_item.volume
        previous_item.condition = new_item.condition
        previous_item.arbitrary_data = new_item.arbitrary_data
        previous_item.tray_id = new_item.tray_id
        previous_item.container_type_id = new_item.container_type_id

        # Clear verification (needs to be re-verified)
        previous_item.verification_job_id = None
        previous_item.scanned_for_verification = False
        previous_item.scanned_for_refile_queue = False
        previous_item.scanned_for_refile = None
        
        # Mark as scanned for this accession job
        previous_item.scanned_for_accession = True
        
        # Reset status
        previous_item.status = ItemStatus.Accessioned
        
        # Mark barcode as no longer withdrawn
        session.execute(
            update(Barcode)
            .where(Barcode.id == new_item.barcode_id)
            .values(withdrawn=False)
        )
        
        new_item = previous_item
    session.add(new_item)
    session.commit()
    session.refresh(new_item)

    # Determine job context — items are linked to accession jobs via tray
    item_job_id = getattr(new_item, 'accession_job_id', None)
    if not item_job_id and hasattr(new_item, 'tray') and new_item.tray:
        item_job_id = new_item.tray.accession_job_id

    item_barcode = new_item.barcode.value if new_item.barcode else str(new_item.id)
    log_audit_event(
        session,
        AuditEventType.ENTITY_CREATED,
        f"Item {item_barcode} scanned for accession",
        entity_type="items",
        entity_id=new_item.id,
        job_type="accession_jobs" if item_job_id else None,
        job_id=item_job_id,
    )
    session.commit()

    return new_item


@router.patch("/{id}", response_model=ItemDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_access_accession", "can_access_verification", any_of=True))])
def update_item(
    id: int, item: ItemUpdateInput, session: Session = Depends(get_session)
):
    """
    Update item details in the database.
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
                key in ["media_type_id", "size_class_id", "owner_id"] # Added owner_id here
                and existing_item.__getattribute__(key) != value
                and existing_item.verification_job_id
            ):
                # V2 FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
                verification_job = (
                    session.execute(select(VerificationJob)
                    .filter(VerificationJob.id == existing_item.verification_job_id))
                    .scalars()
                    .first()
                )
                tray_barcode_val = "N/A"
                if existing_item.tray_id:
                    # V2 FIX: session.exec().first() -> session.execute(select(...)).scalars().first()
                    tray_barcode_obj = session.execute(
                        select(Barcode).join(Tray).where(Tray.id == existing_item.tray_id)
                    ).scalars().first()
                    if tray_barcode_obj:
                        tray_barcode_val = tray_barcode_obj.value
                # --- END: FIX FOR NON-TRAY ITEM ---

                item_barcode = session.get(Barcode, existing_item.barcode_id)

                # Determine change type
                change_type = "UnknownEdit"
                if key == "media_type_id": change_type = "MediaTypeEdit"
                elif key == "size_class_id": change_type = "SizeClassEdit"
                elif key == "owner_id": change_type = "OwnerEdit"

                new_verification_change = VerificationChange(
                    workflow_id=verification_job.workflow_id,
                    tray_barcode_value=tray_barcode_val,
                    item_barcode_value=item_barcode.value,
                    change_type=(
                        "MediaTypeEdit" if key == "media_type_id" else "SizeClassEdit"
                    ),
                    completed_by_id=verification_job.assigned_user_id,
                )

                session.add(new_verification_change)

            setattr(existing_item, key, value)
        setattr(existing_item, "update_dt", datetime.now(timezone.utc))

        session.add(existing_item)
        session.commit()
        session.refresh(existing_item)

        # Determine active job context for this item update
        item_job_type = None
        item_job_id = None
        if getattr(existing_item, 'verification_job_id', None):
            item_job_type = "verification_jobs"
            item_job_id = existing_item.verification_job_id
        elif hasattr(existing_item, 'tray') and existing_item.tray:
            if existing_item.tray.verification_job_id:
                item_job_type = "verification_jobs"
                item_job_id = existing_item.tray.verification_job_id
            elif existing_item.tray.shelving_job_id:
                item_job_type = "shelving_jobs"
                item_job_id = existing_item.tray.shelving_job_id
            elif existing_item.tray.accession_job_id:
                item_job_type = "accession_jobs"
                item_job_id = existing_item.tray.accession_job_id

        item_bc = existing_item.barcode.value if existing_item.barcode else str(id)
        log_audit_event(
            session,
            AuditEventType.ENTITY_UPDATED,
            f"Item {item_bc} updated",
            entity_type="items",
            entity_id=id,
            job_type=item_job_type,
            job_id=item_job_id,
        )
        session.commit()

        return existing_item

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_access_accession"))])
def delete_item(id: int, session: Session = Depends(get_session)):
    """
    Delete an item by its ID.
    """

    item = session.get(Item, id)

    if item:
        item_del_bc = item.barcode.value if item.barcode else str(id)
        log_audit_event(
            session,
            AuditEventType.ENTITY_DELETED,
            f"Item {item_del_bc} deleted",
            entity_type="items",
            entity_id=id,
        )
        session.delete(item)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Item ID {id} Not Found")


@router.post("/move/{barcode_value}", response_model=ItemDetailReadOutput, dependencies=[Depends(RequiresPermission("can_move_trays_and_items"))])
def move_item(
    barcode_value: str,
    item_input: ItemMoveInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
):
    """
    Move an item from one location to another.
    """
    # V2 FIX: session.query().where().first() -> session.execute(select(...)).scalars().first()
    item_lookup_barcode_value = (
        session.execute(select(Barcode).where(Barcode.value == barcode_value))
        .scalars()
        .first()
    )
    if not item_lookup_barcode_value:
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} Item with barcode not found"
        )
    # V2 FIX
    tray_look_barcode_value = (
        session.execute(select(Barcode).where(Barcode.value == item_input.tray_barcode_value))
        .scalars()
        .first()
    )

    if not tray_look_barcode_value:
        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Tray barcode value {item_input.tray_barcode_value} not found"""
        )

    # V2 FIX
    item = (
        session.execute(select(Item).filter(Item.barcode_id == item_lookup_barcode_value.id))
        .scalars()
        .first()
    )

    if not item:
        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Item barcode value {item_lookup_barcode_value.value} not found"""
        )

    # V2 FIX
    src_tray = session.execute(select(Tray).filter(Tray.id == item.tray_id)).scalars().first()
    # V2 FIX
    dest_tray = session.execute(select(Tray).filter(Tray.barcode_id == tray_look_barcode_value.id)).scalars().first()
    # V2 FIX
    current_assigned_location = (
        session.execute(select(ShelfPosition).filter(
            ShelfPosition.id == dest_tray.shelf_position_id
        ))
        .scalars()
        .first()
    ).location
    assigned_location = None
    if src_tray and src_tray.shelf_position_id:
        # V2 FIX
        assigned_location = (
            session.execute(select(ShelfPosition).filter(
                ShelfPosition.id == src_tray.shelf_position_id
            ))
            .scalars()
            .first()
        ).location

    if not src_tray:
        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Tray Item not found"""
        )
    
    # ... (rest of the logic remains the same, relying on correct relationship loading) ...

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

@router.get("/{barcode_value}/ils-metadata", response_model=ILSItemMetadata, dependencies=[Depends(RequiresPermission("can_access_item_detail"))])
def get_ils_metadata(barcode_value: str, session: Session = Depends(get_session)):
    """
    JIT Metadata Endpoint: Resolves the active ILS configuration for an item's owner and 
    fetches live metadata directly without persisting it to the local catalog.
    """
    item = session.execute(
        select(Item).join(Barcode, Item.barcode_id == Barcode.id).filter(Barcode.value == barcode_value)
    ).scalars().first()
    
    owner_id = None
    if item:
        owner_id = item.owner_id
    else:
        non_tray_item = session.execute(
            select(NonTrayItem).join(Barcode, NonTrayItem.barcode_id == Barcode.id).filter(Barcode.value == barcode_value)
        ).scalars().first()
        if non_tray_item:
            owner_id = non_tray_item.owner_id
            
    if not owner_id:
        raise NotFound(detail=f"Item with barcode {barcode_value} not found")
        
    owner = session.get(Owner, owner_id)
    if not owner or not owner.resolved_ils_configuration_id:
        raise NotFound(detail="No active ILS configuration found for this item's owner.")
        
    config = session.get(ILSConfiguration, owner.resolved_ils_configuration_id)
    if not config or not config.is_active or not config.enable_jit_metadata_hook:
        raise BadRequest(detail="JIT Metadata Hook is disabled or configuration inactive for this owner.")
        
    try:
        adapter = get_ils_adapter(config)
        metadata = adapter.fetch_item_metadata(barcode_value)
        if not metadata:
            raise NotFound(detail="Metadata not found in the remote ILS.")
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        inventory_logger.error(f"Failed to fetch JIT metadata for {barcode_value}: {e}")
        raise InternalServerError(detail="Remote ILS connection failed or timed out.")
