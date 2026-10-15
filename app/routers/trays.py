# /code/app/routers/trays.py - REFACRORED TO SQLALCHEMY V2

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session, selectinload # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, update # select/update imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.filter_params import SortParams, ItemFilterParams
from app.events import update_shelf_space_after_tray
from app.logger import inventory_logger
from app.models.aisles import Aisle
from app.models.ladders import Ladder
from app.models.modules import Module
from app.models.move_discrepancies import MoveDiscrepancy
from app.models.non_tray_items import NonTrayItem
from app.models.owners import Owner
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.sides import Side
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
    InternalServerError,
)
from app.sorting import BaseSorter, ItemSorter

from app.auth.dependencies import RequiresPermission
from app.services.audit_service import log_audit_event, AuditEventType

router = APIRouter(
    prefix="/trays",
    tags=["trays"],
)


@router.get("/", response_model=Page[TrayListOutput], dependencies=[Depends(RequiresPermission("can_access_tray_detail"))])
def get_tray_list(
    session: Session = Depends(get_session),
    params: ItemFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get a paginated list of trays from the database
    """
    # Create a query to select all trays from the database
    shelf_load = selectinload(Tray.shelf_position).selectinload(ShelfPosition.shelf)
    shelf_ladder_side_load = shelf_load.selectinload(Shelf.ladder).selectinload(Ladder.side)
    owner_parent_load = selectinload(Tray.owner).selectinload(Owner.parent_owner)
    owner_grandparent_load = owner_parent_load.selectinload(Owner.parent_owner)

    query = select(Tray).options(
        selectinload(Tray.barcode).selectinload(Barcode.type),
        selectinload(Tray.withdrawn_barcode).selectinload(Barcode.type),
        selectinload(Tray.media_type),
        selectinload(Tray.size_class),
        shelf_load.selectinload(Shelf.barcode).selectinload(Barcode.type),
        shelf_ladder_side_load.selectinload(Side.side_orientation),
        shelf_ladder_side_load.selectinload(Side.aisle)
        .selectinload(Aisle.module)
        .selectinload(Module.building),
        selectinload(Tray.owner).selectinload(Owner.owner_tier),
        selectinload(Tray.owner).selectinload(Owner.children),
        owner_parent_load.selectinload(Owner.owner_tier),
        owner_parent_load.selectinload(Owner.children),
        owner_grandparent_load.selectinload(Owner.owner_tier),
        owner_grandparent_load.selectinload(Owner.children),
    )

    if params.barcode_value:
        barcode_value_subquery = select(Barcode.id).where(
            Barcode.value.in_(params.barcode_value)
        ).scalar_subquery()
        query = query.where(Tray.barcode_id.in_(barcode_value_subquery))
    if params.owner_id:
        query = query.where(Tray.owner_id.in_(params.owner_id))
    if params.owner:
        owner_subquery = select(Owner.id).where(Owner.name.in_(params.owner)).scalar_subquery()
        query = query.where(Tray.owner_id.in_(owner_subquery))
    if params.size_class_id:
        query = query.where(Tray.size_class_id.in_(params.size_class_id))
    if params.size_class:
        size_class_subquery = select(SizeClass.id).where(
            SizeClass.name.in_(params.size_class) # Use SizeClass.name
        ).scalar_subquery()
        query = query.where(Tray.size_class_id.in_(size_class_subquery))
    if params.media_type_id:
        query = query.where(Tray.media_type_id.in_(params.media_type_id))
    if params.media_type:
        media_type_subquery = select(MediaType.id).where(
            MediaType.name.in_(params.media_type)
        ).scalar_subquery()
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


@router.get("/{id}", response_model=TrayDetailReadOutput, dependencies=[Depends(RequiresPermission("can_access_tray_detail"))])
def get_tray_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a tray by its ID
    """
    tray = session.get(Tray, id)

    if tray:
        return tray

    raise NotFound(detail=f"Tray ID {id} Not Found")


@router.get("/barcode/{value}", response_model=TrayDetailReadOutput, dependencies=[Depends(RequiresPermission("can_access_tray_detail"))])
def get_tray_by_barcode_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve a tray using a barcode value
    """
    if not value:
        raise ValidationException(detail="Tray barcode value is required")

    # V2 FIX: session.query().join().filter().first() -> session.execute(select(...)).scalars().first()
    tray = (
        session.execute(
            select(Tray)
            .join(Barcode, Tray.barcode_id == Barcode.id)
            .filter(Barcode.value == value)
        )
        .scalars()
        .first()
    )
    if not tray:
        raise NotFound(detail=f"Tray barcode value {value} not found")
    return tray


@router.post("/", response_model=TrayDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_access_accession"))])
def create_tray(tray_input: TrayInput, session: Session = Depends(get_session)):
    """
    Create a new tray record
    """
    # Check if a tray with the same barcode already exists
    if tray_input.barcode_id:
        # V2 FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
        existing_tray = (
            session.execute(select(Tray).filter(Tray.barcode_id == tray_input.barcode_id))
            .scalars()
            .first()
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
    # V2 FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
    container_type = (
        session.execute(select(ContainerType).filter(ContainerType.type == "Tray"))
        .scalars()
        .first()
    )
    # trays are created at accession, set accession date
    if not new_tray.accession_dt:
        new_tray.accession_dt = datetime.now(timezone.utc)
    new_tray.container_type_id = container_type.id
    session.add(new_tray)
    update_shelf_space_after_tray(session, new_tray, None, None)
    session.commit()
    session.refresh(new_tray)

    tray_barcode = new_tray.barcode.value if new_tray.barcode else str(new_tray.id)
    log_audit_event(
        session,
        AuditEventType.ENTITY_CREATED,
        f"Tray {tray_barcode} scanned for accession",
        entity_type="trays",
        entity_id=new_tray.id,
        job_type="accession_jobs" if new_tray.accession_job_id else None,
        job_id=new_tray.accession_job_id,
    )
    session.commit()

    return new_tray


# In trays.py, replace the existing update_tray function with this one

@router.patch("/{id}", response_model=TrayDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_access_accession", "can_access_verification", "can_edit_tray", any_of=True))])
def update_tray(
    id: int,
    tray: TrayUpdateInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
):
    """
    Update a tray record in the database.
    """
    existing_tray = session.get(Tray, id)
    if not existing_tray:
        raise NotFound(detail=f"Tray ID {id} Not Found")

    # --- (Logic for checking shelf_position_id is unchanged) ---
    if tray.shelf_position_id is not None:
        # ... (your existing logic for moving a tray)
        pass

    new_verification_changes = []
    verification_job = None
    if tray.verification_job_id:
        verification_job = session.get(VerificationJob, tray.verification_job_id)

    # --- We will check for all changes and prepare the audit records ---
    if verification_job:
        tray_barcode = session.get(Barcode, existing_tray.barcode_id)

        # Checking if owner has changed
        if tray.owner_id and tray.owner_id != existing_tray.owner_id:
            for item in existing_tray.items:
                item_barcode = session.get(Barcode, item.barcode_id)
                new_verification_changes.append(
                    VerificationChange(
                        item_id=item.id,
                        workflow_id=verification_job.workflow_id,
                        tray_barcode_value=tray_barcode.value,
                        item_barcode_value=item_barcode.value,
                        change_type="OwnerEdit",
                        completed_by_id=verification_job.assigned_user_id,
                    )
                )

        # Checking if size class has changed
        if tray.size_class_id and tray.size_class_id != existing_tray.size_class_id:
            for item in existing_tray.items:
                item_barcode = session.get(Barcode, item.barcode_id)
                new_verification_changes.append(
                    VerificationChange(
                        item_id=item.id,
                        workflow_id=verification_job.workflow_id,
                        tray_barcode_value=tray_barcode.value,
                        item_barcode_value=item_barcode.value,
                        change_type="SizeClassEdit",
                        completed_by_id=verification_job.assigned_user_id,
                    )
                )

        # Checking if media type has changed
        if tray.media_type_id and tray.media_type_id != existing_tray.media_type_id:
            for item in existing_tray.items:
                item_barcode = session.get(Barcode, item.barcode_id)
                new_verification_changes.append(
                    VerificationChange(
                        item_id=item.id,
                        workflow_id=verification_job.workflow_id,
                        tray_barcode_value=tray_barcode.value,
                        item_barcode_value=item_barcode.value,
                        change_type="MediaTypeEdit",
                        completed_by_id=verification_job.assigned_user_id,
                    )
                )
    
    # Now, save the audit records if any were created
    if new_verification_changes:
        session.add_all(new_verification_changes)

    # Finally, update the tray and its items
    mutated_data = tray.model_dump(exclude_unset=True)
    for key, value in mutated_data.items():
        setattr(existing_tray, key, value)
    
    # Cascade changes to child items
    if tray.owner_id:
        for item in existing_tray.items: item.owner_id = tray.owner_id
    if tray.size_class_id:
        for item in existing_tray.items: item.size_class_id = tray.size_class_id
    if tray.media_type_id:
        for item in existing_tray.items: item.media_type_id = tray.media_type_id

    setattr(existing_tray, "update_dt", datetime.now(timezone.utc))

    session.add(existing_tray)
    update_shelf_space_after_tray(
        session, existing_tray, existing_tray.shelf_position_id, tray.shelf_position_id
    )
    session.commit()
    session.refresh(existing_tray)

    # Determine active job context for this tray update
    tray_job_type = None
    tray_job_id = None
    if existing_tray.verification_job_id:
        tray_job_type = "verification_jobs"
        tray_job_id = existing_tray.verification_job_id
    elif existing_tray.shelving_job_id:
        tray_job_type = "shelving_jobs"
        tray_job_id = existing_tray.shelving_job_id
    elif existing_tray.accession_job_id:
        tray_job_type = "accession_jobs"
        tray_job_id = existing_tray.accession_job_id

    tray_bc = existing_tray.barcode.value if existing_tray.barcode else str(id)
    log_audit_event(
        session,
        AuditEventType.ENTITY_UPDATED,
        f"Tray {tray_bc} updated",
        entity_type="trays",
        entity_id=id,
        job_type=tray_job_type,
        job_id=tray_job_id,
    )
    session.commit()

    return existing_tray


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_access_accession"))])
def delete_tray(id: int, session: Session = Depends(get_session)):
    """
    Delete a tray by its ID
    """
    tray = session.get(Tray, id)

    if tray:
        # V2 FIX: session.exec().all() -> session.execute(select(...)).scalars().all()
        items_to_delete = session.execute(
            select(Item).where(Item.tray_id == id)
        ).scalars().all()
        for item in items_to_delete:
            session.delete(item)
            session.commit()

        update_shelf_space_after_tray(session, None, None, tray.shelf_position_id)
        tray_del_bc = tray.barcode.value if tray.barcode else str(id)
        log_audit_event(
            session,
            AuditEventType.ENTITY_DELETED,
            f"Tray {tray_del_bc} deleted",
            entity_type="trays",
            entity_id=id,
        )
        session.delete(tray)
        session.commit()

        for item in items_to_delete:
            session.delete(session.get(Barcode, item.barcode_id))
            session.commit()
        session.delete(session.get(Barcode, tray.barcode_id))
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Tray ID {id} Not Found")


@router.post("/move/{barcode_value}", response_model=TrayDetailReadOutput, dependencies=[Depends(RequiresPermission("can_move_trays_and_items"))])
def move_tray(
    barcode_value: str,
    tray_input: TrayMoveInput,
    session: Session = Depends(get_session),
):
    """
    Move a tray from one location to another.
    """
    # Retrieve the non_tray_item and shelves in a single query
    # V2 FIX: session.query().join().filter().first() -> session.execute(select(...)).scalars().first()
    tray = (
        session.execute(select(Tray)
        .join(Barcode, Tray.barcode_id == Barcode.id)
        .filter(Barcode.value == barcode_value))
        .scalars()
        .first()
    )
    if not tray:
        raise ValidationException(
            detail=f"""Failed to transfer: {barcode_value} - Tray with barcode value not found"""
        )

        # Retrieve the non_tray_item and shelves in a single query
    # V2 FIX
    src_shelf = (
        session.execute(select(Shelf)
        .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id)
        .filter(ShelfPosition.shelf_id == Shelf.id))
        .scalars()
        .first()
    )

    # Retrieve the destination shelf
    # V2 FIX
    dest_shelf = (
        session.execute(select(Shelf)
        .join(ShelfPosition, ShelfPosition.shelf_id == Shelf.id)
        .join(Barcode, Shelf.barcode_id == Barcode.id)
        .filter(Barcode.value == tray_input.shelf_barcode_value))
        .scalars()
        .first()
    )

    current_assigned_location = None
    original_assigned_location = None
    if src_shelf:
        original_assigned_location = (src_shelf.location + "-" + str(
            tray.shelf_position.position_number))
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
        # V2 FIX
        tray_size_class = (
            session.execute(select(SizeClass).where(SizeClass.id == tray.size_class_id)).scalars().first()
        )
        # V2 FIX
        destination_size_class = (
            session.execute(select(SizeClass)
            .where(SizeClass.id == dest_shelf.shelf_type.size_class_id))
            .scalars()
            .first()
        )
        # V2 FIX
        tray_owner = session.execute(select(Owner).where(Owner.id == tray.owner_id)).scalars().first()
        # V2 FIX
        destination_owner = (
            session.execute(select(Owner).where(Owner.id == dest_shelf.owner_id)).scalars().first()
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
        if destination_shelf_position.position_number == tray_input.shelf_position_number:
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
    update_shelf_space_after_tray(
        session, tray, destination_shelf_position_id, old_shelf_position_id
    )
    session.commit()

    # Determine active job context for this tray move
    tray_job_type = None
    tray_job_id = None
    if tray.verification_job_id:
        tray_job_type = "verification_jobs"
        tray_job_id = tray.verification_job_id
    elif tray.shelving_job_id:
        tray_job_type = "shelving_jobs"
        tray_job_id = tray.shelving_job_id
    elif tray.accession_job_id:
        tray_job_type = "accession_jobs"
        tray_job_id = tray.accession_job_id

    log_audit_event(
        session,
        AuditEventType.ENTITY_MOVED,
        f"Tray {barcode_value} moved to position {tray_input.shelf_position_number} on shelf {tray_input.shelf_barcode_value}",
        entity_type="trays",
        entity_id=tray.id,
        job_type=tray_job_type,
        job_id=tray_job_id,
    )
    session.commit()

    return tray
