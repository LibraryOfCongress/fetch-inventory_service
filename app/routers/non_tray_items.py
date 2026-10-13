# /code/app/routers/non_tray_items.py - REFACRORED TO SQLALCHEMY V2

from io import StringIO
from typing import Optional

import pandas as pd
from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, update     # select is imported from sqlalchemy now
from datetime import datetime, timezone

from starlette.responses import StreamingResponse

from app.database.session import get_session, commit_record
from app.events import update_shelf_space_after_non_tray
from app.filter_params import SortParams
from app.logger import inventory_logger
from app.models.media_types import MediaType
from app.models.move_discrepancies import MoveDiscrepancy
from app.models.non_tray_items import NonTrayItem, NonTrayItemStatus
from app.models.barcodes import Barcode
from app.models.container_types import ContainerType
from app.models.owners import Owner
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.items import Item
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.models.shelving_jobs import ShelvingJob
from app.models.size_class import SizeClass
from app.models.trays import Tray
from app.models.verification_changes import VerificationChange
from app.models.verification_jobs import VerificationJob
from app.models.items import Item, ILSSyncState
from app.models.accession_jobs import AccessionJob
from app.models.ils_configurations import ILSConfiguration
from app.ils.factory import get_ils_adapter
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

from app.auth.dependencies import RequiresPermission
from app.services.audit_service import log_audit_event, AuditEventType

router = APIRouter(
    prefix="/non_tray_items",
    tags=["non tray items"],
)


@router.get("/", response_model=Page[NonTrayItemListOutput], dependencies=[Depends(RequiresPermission("can_access_item_detail"))])
def get_non_tray_item_list(
    session: Session = Depends(get_session),
    params: ItemFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get a paginated list of non tray items from the database
    """
    # Create a query to select all non tray items from the database
    query = select(NonTrayItem)

    if params.barcode_value:
        barcode_value_subquery = select(Barcode.id).where(
            Barcode.value.in_(params.barcode_value)
        ).scalar_subquery()
        query = query.where(NonTrayItem.barcode_id.in_(barcode_value_subquery))
    if params.status:
        query = query.where(NonTrayItem.status.in_(params.status))
    if params.owner_id:
        query = query.where(NonTrayItem.owner_id.in_(params.owner_id))
    if params.owner:
        owner_subquery = select(Owner.id).where(Owner.name.in_(params.owner)).scalar_subquery()
        query = query.where(NonTrayItem.owner_id.in_(owner_subquery))
    if params.size_class_id:
        query = query.where(NonTrayItem.size_class_id.in_(params.size_class_id))
    if params.size_class:
        size_class_subquery = select(SizeClass.id).where(
            SizeClass.name.in_(params.size_class)
        ).scalar_subquery()
        query = query.where(NonTrayItem.size_class_id.in_(size_class_subquery))
    if params.media_type_id:
        query = query.where(NonTrayItem.media_type_id.in_(params.media_type_id))
    if params.media_type:
        media_type_subquery = select(MediaType.id).where(
            MediaType.name.in_(params.media_type)
        ).scalar_subquery()
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


@router.get("/download", response_class=StreamingResponse, dependencies=[Depends(RequiresPermission("can_access_item_detail"))])
def download_non_tray_items(
    session: Session = Depends(get_session),
    params: ItemFilterParams = Depends(),
):
    """
    Get a paginated list of non tray items from the database
    """
    # Create a query to select all non tray items from the database
    query = (
        select(
            NonTrayItem.accession_dt,
            NonTrayItem.status,
            Owner.name.label("owner_name"),
            SizeClass.name.label("size_class_name"),
            MediaType.name.label("media_type_name"),
            Barcode.value.label("barcode_value"),
        )
        .outerjoin(Owner, NonTrayItem.owner_id == Owner.id)
        .outerjoin(SizeClass, NonTrayItem.size_class_id == SizeClass.id)
        .outerjoin(MediaType, NonTrayItem.media_type_id == MediaType.id)
        .outerjoin(Barcode, NonTrayItem.barcode_id == Barcode.id)
    )
    # ... (rest of filtering logic is unchanged) ...
    if params.barcode_value:
        query = query.where(Barcode.value.in_(params.barcode_value))
    if params.status:
        query = query.where(NonTrayItem.status.in_(params.status))
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
        result = session.execute(query) # V2 EXECUTION
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

@router.get("/{id}", response_model=NonTrayItemDetailReadOutput, dependencies=[Depends(RequiresPermission("can_access_item_detail"))])
def get_non_tray_item_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a non_tray_item by its ID
    """
    non_tray_item = session.get(NonTrayItem, id)

    if non_tray_item:
        return non_tray_item

    raise NotFound(detail=f"Non Tray Item ID {id} Not Found")


@router.get("/barcode/{value}", response_model=NonTrayItemDetailReadOutput, dependencies=[Depends(RequiresPermission("can_access_item_detail"))])
def get_non_tray_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a non-tray using a barcode value
    """
    if not value:
        raise ValidationException(detail="Non Tray Item barcode value is required")

    # V2 FIX: session.query().join().filter().first() -> session.execute(select(...)).scalars().first()
    non_tray = (
        session.execute(
            select(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .filter(Barcode.value == value)
        )
        .scalars()
        .first()
    )
    if not non_tray:
        raise NotFound(detail=f"Non Tray Item barcode value {value} Not Found")
    return non_tray


@router.post("/", response_model=NonTrayItemDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_access_accession"))])
def create_non_tray_item(
    item_input: NonTrayItemInput, 
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None
):
    """
    Create a new non_tray_item record
    """
    # check if barcode is already in use
    # V2 FIX: session.query().where().first() -> session.execute(select(...)).scalars().first()
    item = session.execute(select(Item).where(Item.barcode_id == item_input.barcode_id)).scalars().first()
    # V2 FIX
    non_tray_item = (
        session.execute(select(NonTrayItem).where(NonTrayItem.barcode_id == item_input.barcode_id))
        .scalars()
        .first()
    )
    if item or non_tray_item:
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

    # Create a new non_tray_item
    new_non_tray_item = NonTrayItem(**item_input.model_dump())
    new_non_tray_item.withdrawal_dt = None
    # default to non-tray container_type
    # V2 FIX
    container_type = (
        session.execute(select(ContainerType).filter(ContainerType.type == "Non-Tray"))
        .scalars()
        .first()
    )
    new_non_tray_item.withdrawal_dt = None
    new_non_tray_item.container_type_id = container_type.id
    # non-trays are created in accession, set accession date
    if not new_non_tray_item.accession_dt:
        new_non_tray_item.accession_dt = datetime.now(timezone.utc)

    # Set default status to Accessioned for new non-tray items
    new_non_tray_item.status = NonTrayItemStatus.Accessioned
    
    if ils_sync_state:
        new_non_tray_item.ils_sync_state = ils_sync_state
    
    # check if existing withdrawn non-tray with this barcode
    # Query by withdrawn_barcode_id since withdrawn items have barcode_id = None
    previous_non_tray_item = session.execute(
        select(NonTrayItem).where(
            NonTrayItem.withdrawn_barcode_id == new_non_tray_item.barcode_id
        )
    ).scalars().first()
    
    if previous_non_tray_item:
        # Reuse the existing withdrawn non-tray item record
        # Restore barcode relationship
        previous_non_tray_item.barcode_id = new_non_tray_item.barcode_id
        previous_non_tray_item.withdrawn_barcode_id = None
        
        # Clear withdrawal tracking fields
        previous_non_tray_item.withdrawal_dt = None
        previous_non_tray_item.withdrawn_location = None
        previous_non_tray_item.withdrawn_internal_location = None
        previous_non_tray_item.withdrawn_loc_bcodes = None
        
        # Update with new accession data
        previous_non_tray_item.accession_dt = datetime.now(timezone.utc)
        previous_non_tray_item.accession_job_id = new_non_tray_item.accession_job_id
        previous_non_tray_item.owner_id = new_non_tray_item.owner_id
        previous_non_tray_item.size_class_id = new_non_tray_item.size_class_id
        previous_non_tray_item.media_type_id = new_non_tray_item.media_type_id
        previous_non_tray_item.subcollection_id = new_non_tray_item.subcollection_id
        previous_non_tray_item.container_type_id = new_non_tray_item.container_type_id
        
        # Clear verification and shelving (needs to be re-verified)
        previous_non_tray_item.verification_job_id = None
        previous_non_tray_item.scanned_for_verification = False
        previous_non_tray_item.scanned_for_shelving = False
        previous_non_tray_item.scanned_for_refile_queue = False
        previous_non_tray_item.scanned_for_refile = None
        previous_non_tray_item.shelf_position_id = None
        previous_non_tray_item.shelf_position_proposed_id = None
        previous_non_tray_item.shelving_job_id = None
        
        # Mark as scanned for this accession job
        previous_non_tray_item.scanned_for_accession = True
        
        # Reset status
        previous_non_tray_item.status = NonTrayItemStatus.Accessioned
        
        # Mark barcode as no longer withdrawn
        session.execute(
            update(Barcode)
            .where(Barcode.id == new_non_tray_item.barcode_id)
            .values(withdrawn=False)
        )
        
        new_non_tray_item = previous_non_tray_item

    session.add(new_non_tray_item)
    update_shelf_space_after_non_tray(session, new_non_tray_item, None, None)
    session.commit()
    session.refresh(new_non_tray_item)

    nti_barcode = new_non_tray_item.barcode.value if new_non_tray_item.barcode else str(new_non_tray_item.id)
    log_audit_event(
        session,
        AuditEventType.ENTITY_CREATED,
        f"Non-tray item {nti_barcode} scanned for accession",
        entity_type="non_tray_items",
        entity_id=new_non_tray_item.id,
        job_type="accession_jobs" if new_non_tray_item.accession_job_id else None,
        job_id=new_non_tray_item.accession_job_id,
    )
    session.commit()

    return new_non_tray_item


@router.patch("/{id}", response_model=NonTrayItemDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_access_accession", "can_access_verification", "can_edit_non_tray_item", any_of=True))])
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
        # V2 FIX
        new_shelf_position = (
            session.execute(select(ShelfPosition)
            .filter(ShelfPosition.id == non_tray_item.shelf_position_id))
            .scalars()
            .first()
        )

        if not new_shelf_position:
            raise NotFound(
                detail=f"Shelf Position ID {non_tray_item.shelf_position_id} Not Found"
            )
        
        # V2 FIX
        shelf = (
            session.execute(select(Shelf).filter(Shelf.id == new_shelf_position.shelf_id))
            .scalars()
            .first()
        )

        if not shelf:
            raise NotFound(detail=f"Shelf ID {new_shelf_position.shelf_id} Not Found")

        if existing_non_tray_item.shelf_position_id and (
            non_tray_item.shelf_position_id != existing_non_tray_item.shelf_position_id
        ):
            # V2 FIX
            existing_shelf_position = (
                session.execute(select(ShelfPosition)
                .filter(ShelfPosition.id == existing_non_tray_item.shelf_position_id))
                .scalars()
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
            # V2 FIX
            verification_job = (
                session.execute(select(VerificationJob)
                .filter(
                    VerificationJob.id == existing_non_tray_item.verification_job_id
                ))
                .scalars()
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
                completed_by_id=verification_job.assigned_user_id,
            )

            session.add(new_verification_change)

        setattr(existing_non_tray_item, key, value)
    setattr(existing_non_tray_item, "update_dt", datetime.now(timezone.utc))

    # Commit the changes to the database
    session.add(existing_non_tray_item)
    update_shelf_space_after_non_tray(
        session,
        existing_non_tray_item,
        existing_non_tray_item.shelf_position_id,
        non_tray_item.shelf_position_id,
    )
    session.commit()
    session.refresh(existing_non_tray_item)

    # Determine active job context for this non-tray item update
    nti_job_type = None
    nti_job_id = None
    if existing_non_tray_item.verification_job_id:
        nti_job_type = "verification_jobs"
        nti_job_id = existing_non_tray_item.verification_job_id
    elif existing_non_tray_item.shelving_job_id:
        nti_job_type = "shelving_jobs"
        nti_job_id = existing_non_tray_item.shelving_job_id
    elif existing_non_tray_item.accession_job_id:
        nti_job_type = "accession_jobs"
        nti_job_id = existing_non_tray_item.accession_job_id

    nti_bc = existing_non_tray_item.barcode.value if existing_non_tray_item.barcode else str(id)
    log_audit_event(
        session,
        AuditEventType.ENTITY_UPDATED,
        f"Non-tray item {nti_bc} updated",
        entity_type="non_tray_items",
        entity_id=id,
        job_type=nti_job_type,
        job_id=nti_job_id,
    )
    session.commit()

    return existing_non_tray_item


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_access_accession"))])
def delete_non_tray_item(id: int, session: Session = Depends(get_session)):
    """
    Delete a non_tray_item by its ID
    """
    non_tray_item = session.get(NonTrayItem, id)

    if non_tray_item:
        update_shelf_space_after_non_tray(session, None, None, non_tray_item.shelf_position_id)
        nti_del_bc = non_tray_item.barcode.value if non_tray_item.barcode else str(id)
        log_audit_event(
            session,
            AuditEventType.ENTITY_DELETED,
            f"Non-tray item {nti_del_bc} deleted",
            entity_type="non_tray_items",
            entity_id=id,
        )
        session.delete(non_tray_item)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Non Tray Item ID {id} Not Found")


@router.post("/move/{barcode_value}", response_model=NonTrayItemDetailReadOutput, dependencies=[Depends(RequiresPermission("can_move_trays_and_items"))])
def move_item(
    barcode_value: str,
    non_tray_item_input: NonTrayItemMoveInput,
    session: Session = Depends(get_session),
):
    """
    Move a non_tray_item from one location to another.
    """
    # Retrieve the non_tray_item and shelves in a single query
    # V2 FIX
    non_tray_item = (
        session.execute(
            select(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .filter(Barcode.value == barcode_value)
        )
        .scalars()
        .first()
    )
    if not non_tray_item:
        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Non Tray Item with barcode value not found"""
        )

    # V2 FIX
    src_shelf = (
        session.execute(
            select(Shelf)
            .join(ShelfPosition, non_tray_item.shelf_position_id == ShelfPosition.id)
            .filter(ShelfPosition.shelf_id == Shelf.id)
        )
        .scalars()
        .first()
    )

    # Retrieve the destination shelf
    # V2 FIX
    dest_shelf = (
        session.execute(
            select(Shelf)
            .join(Barcode, Shelf.barcode_id == Barcode.id)
            .filter(Barcode.value == non_tray_item_input.shelf_barcode_value)
        )
        .scalars()
        .first()
    )

    original_assigned_location = None
    current_assigned_location = None
    if src_shelf:
        original_assigned_location = (src_shelf.location + "-" + str(
            non_tray_item.shelf_position.position_number
        ))
    if dest_shelf:
        current_assigned_location = (dest_shelf.location + "-" + str(
            non_tray_item_input.shelf_position_number
        ))

    if (
        not non_tray_item.scanned_for_accession
        or not non_tray_item.scanned_for_verification
    ):
        new_move_discrepancy = MoveDiscrepancy(
            non_tray_item_id=non_tray_item.id,
            assigned_user_id=non_tray_item_input.assigned_user_id,
            owner_id=non_tray_item.owner_id,
            size_class_id=non_tray_item.size_class_id,
            container_type_id=non_tray_item.container_type_id,
            original_assigned_location=original_assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Accessioned Discrepancy - Container barcode {barcode_value} has not been accessioned or verified"""
        )

        commit_record(session, new_move_discrepancy)
        raise ValidationException(
            detail=f"Failed to transfer: {barcode_value} has not been accessioned or verified"
        )

    if (
        non_tray_item.status != "In" or
        non_tray_item.shelf_position_id is None or
        non_tray_item.withdrawn_barcode_id is not None or
        not src_shelf
    ):

        new_move_discrepancy = MoveDiscrepancy(
            non_tray_item_id=non_tray_item.id,
            assigned_user_id=non_tray_item_input.assigned_user_id,
            owner_id=non_tray_item.owner_id,
            size_class_id=non_tray_item.size_class_id,
            container_type_id=non_tray_item.container_type_id,
            original_assigned_location=original_assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Shelved Discrepancy - Container barcode {barcode_value} was not previously shelved"""
        )

        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Container has not been assigned to a shelf position"""
        )

    if not dest_shelf:
        new_move_discrepancy = MoveDiscrepancy(
            non_tray_item_id=non_tray_item.id,
            assigned_user_id=non_tray_item_input.assigned_user_id,
            owner_id=non_tray_item.owner_id,
            size_class_id=non_tray_item.size_class_id,
            container_type_id=non_tray_item.container_type_id,
            original_assigned_location=original_assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Not Shelved Discrepancy - Destination shelf with barcode {barcode_value} not found""",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Destination Shelf with
            barcode value {non_tray_item_input.shelf_barcode_value} not found"""
        )

    # Check if the source and destination shelves are of the same size class
    if (
        src_shelf.shelf_type.size_class_id
        != dest_shelf.shelf_type.size_class_id
        or src_shelf.owner_id != dest_shelf.owner_id
    ):
        # V2 FIX
        non_tray_item_size_class = (
            session.execute(select(SizeClass).where(SizeClass.id == non_tray_item.size_class_id))
            .scalars()
            .first()
        )
        # V2 FIX
        destination_size_class = (
            session.execute(select(SizeClass).where(SizeClass.id == dest_shelf.shelf_type.size_class_id))
            .scalars()
            .first()
        )
        # V2 FIX
        non_tray_item_owner = (
            session.execute(select(Owner).where(Owner.id == non_tray_item.owner_id))
            .scalars()
            .first()
        )
        # V2 FIX
        destination_owner = (
            session.execute(select(Owner).where(Owner.id == dest_shelf.owner_id))
            .scalars()
            .first()
        )
        # Create a Discrepancy
        discrepancy_error = "Unknown"
        if (
            src_shelf.shelf_type.size_class_id
            != dest_shelf.shelf_type.size_class_id
        ):
            discrepancy_error = f"""Size Discrepancy - Container size class: {non_tray_item_size_class.short_name} does not match Shelf size class: {destination_size_class.short_name}"""
        if src_shelf.owner_id != dest_shelf.owner_id:
            discrepancy_error = f"""Owner Discrepancy - Container owner: {non_tray_item_owner.name} does not match Shelf owner: {destination_owner.name}"""

        # V2 FIX
        assigned_location = (
            session.execute(select(ShelfPosition)
            .where(ShelfPosition.id == non_tray_item.shelf_position_id))
            .scalars()
            .first()
        ).location
        current_assigned_location = (dest_shelf.location + "-" +
                                     str(non_tray_item_input.shelf_position_number))

        non_tray_item_input = MoveDiscrepancy(
            non_tray_item_id=non_tray_item.id,
            assigned_user_id=non_tray_item_input.assigned_user_id,
            owner_id=dest_shelf.owner_id,
            size_class_id=dest_shelf.shelf_type.size_class_id,
            container_type_id=non_tray_item.container_type_id,
            original_assigned_location=assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"{discrepancy_error}",
        )
        commit_record(session, non_tray_item_input)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Shelf must be of the same size class and owner."""
        )
    # Check the available space in the destination shelf
    if dest_shelf.available_space < 1:
        # grab shelving job for user_id
        # V2 FIX
        assigned_location = (
            session.execute(select(ShelfPosition)
            .where(ShelfPosition.id == non_tray_item.shelf_position_id))
            .scalars()
            .first()
        ).location

        current_assigned_location = (dest_shelf.location + "-" +
                                     str(non_tray_item_input.shelf_position_number))

        new_move_discrepancy = MoveDiscrepancy(
            non_tray_item_id=non_tray_item.id,
            assigned_user_id=non_tray_item_input.assigned_user_id,
            owner_id=dest_shelf.owner_id,
            size_class_id=dest_shelf.shelf_type.size_class_id,
            container_type_id=non_tray_item.container_type_id,
            original_assigned_location=assigned_location,
            current_assigned_location=current_assigned_location,
            error=f"""Available Space Discrepancy - Shelf {non_tray_item_input.shelf_barcode_value} has no available space""",
        )
        commit_record(session, new_move_discrepancy)

        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Shelf barcode
            {non_tray_item_input.shelf_barcode_value} at location
            {current_assigned_location} has no available space"""
        )

    # Check if the shelf position at destination shelf is unoccupied
    destination_shelf_positions = dest_shelf.shelf_positions
    destination_shelf_position_id = None
    for destination_shelf_position in destination_shelf_positions:
        if destination_shelf_position.position_number == non_tray_item_input.shelf_position_number:
            destination_shelf_position_id = destination_shelf_position.id
            # V2 FIX
            tray_shelf_position = (
                session.execute(select(Tray)
                .filter(Tray.shelf_position_id == destination_shelf_position.id))
                .scalars()
                .first()
            )
            # V2 FIX
            non_tray_shelf_position = (
                session.execute(select(NonTrayItem)
                .filter(NonTrayItem.shelf_position_id == destination_shelf_position.id))
                .scalars()
                .first()
            )

            if tray_shelf_position or non_tray_shelf_position:
                new_move_discrepancy = MoveDiscrepancy(
                    non_tray_item_id=non_tray_item.id,
                    assigned_user_id=non_tray_item_input.assigned_user_id,
                    owner_id=dest_shelf.owner_id,
                    size_class_id=dest_shelf.shelf_type.size_class_id,
                    container_type_id=non_tray_item.container_type_id,
                    original_assigned_location=original_assigned_location,
                    current_assigned_location=current_assigned_location,
                    error=f"""Available Space Discrepancy - Shelf Position
                     {current_assigned_location} is already occupied""",
                )
                commit_record(session, new_move_discrepancy)

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
    src_shelf.update_dt = update_dt
    dest_shelf.update_dt = update_dt

    # Commit the changes
    session.add(non_tray_item)
    session.add(src_shelf)
    session.add(dest_shelf)
    update_shelf_space_after_non_tray(
        session, non_tray_item, destination_shelf_position_id, old_shelf_position_id
    )
    session.commit()
    session.refresh(non_tray_item)
    session.refresh(src_shelf)
    session.refresh(dest_shelf)

    # Determine active job context for this non-tray item move
    nti_job_type = None
    nti_job_id = None
    if non_tray_item.verification_job_id:
        nti_job_type = "verification_jobs"
        nti_job_id = non_tray_item.verification_job_id
    elif non_tray_item.shelving_job_id:
        nti_job_type = "shelving_jobs"
        nti_job_id = non_tray_item.shelving_job_id
    elif non_tray_item.accession_job_id:
        nti_job_type = "accession_jobs"
        nti_job_id = non_tray_item.accession_job_id

    log_audit_event(
        session,
        AuditEventType.ENTITY_MOVED,
        f"Non-tray item {barcode_value} moved to position {non_tray_item_input.shelf_position_number} on shelf {non_tray_item_input.shelf_barcode_value}",
        entity_type="non_tray_items",
        entity_id=non_tray_item.id,
        job_type=nti_job_type,
        job_id=nti_job_id,
    )
    session.commit()

    return non_tray_item
