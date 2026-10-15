
# /app/routers/shipping_jobs.py

from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError


from app.database.session import get_session
from app.filter_params import SortParams, JobFilterParams
from app.models.users import User
from app.models.shipping_jobs import ShippingJob, ShippingJobStatus
from app.models.shipping_bins import ShippingBin, ShippingBinStatus
from app.models.items import Item, ItemStatus
from app.models.non_tray_items import NonTrayItem, NonTrayItemStatus
from app.models.delivery_locations import DeliveryLocation
from app.models.barcodes import Barcode

from app.schemas.shipping_jobs import (
    ShippingJobInput,
    ShippingJobUpdateInput,
    ShippingJobListOutput,
    ShippingJobOutput,
    ShippingJobOutput,
    ShippingBinDetailOutput,
    ShippingItemCheckOutput
)

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.helpers.system_setting_helpers import get_setting_value
from app.utils.job_assignment import auto_assign_on_start, update_status_on_assignment
from app.services.audit_service import log_audit_event, AuditEventType
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
    Forbidden
)

router = APIRouter(
    prefix="/shipping-jobs",
    tags=["shipping jobs"],
    dependencies=[Depends(RequiresPermission("can_access_shipping"))],
)

def check_shipping_enabled(session: Session):
    """
    Check if shipping module is enabled. Raise 403 if disabled.
    """
    enabled = get_setting_value(session, "shipping_module_enabled", "false")
    if enabled.lower() != "true":
        raise Forbidden(detail="Shipping module is disabled")

@router.get("/", response_model=Page[ShippingJobListOutput])
def get_shipping_job_list(
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends(),
):
    """
    List shipping jobs with pagination and filtering.
    """
    query = select(ShippingJob).options(
        selectinload(ShippingJob.assigned_user),
        selectinload(ShippingJob.created_by)
    )

    if params.assigned_user_id:
        query = query.where(ShippingJob.assigned_user_id == params.assigned_user_id)
    if params.assigned_user:
        assigned_user_subquery = select(User.id).where(
            func.concat(User.first_name, " ", User.last_name).in_(
                params.assigned_user
            )
        ).scalar_subquery()
        query = query.where(ShippingJob.assigned_user_id.in_(assigned_user_subquery))
    
    if params.status:
         query = query.where(ShippingJob.status.in_(params.status))
         
    # Default sort by create_dt desc if not specified
    if not sort_params.sort_by:
        query = query.order_by(ShippingJob.create_dt.desc())
        
    return paginate(session, query)

@router.post("/", response_model=ShippingJobOutput, status_code=201, dependencies=[Depends(RequiresPermission("create_shipping_jobs"))])
def create_shipping_job(
    input_data: ShippingJobInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Create a new Shipping Job.
    """
    check_shipping_enabled(session)
    
    new_job = ShippingJob(
        assigned_user_id=input_data.assigned_user_id,
        created_by_id=current_user.id,
        status=ShippingJobStatus.Created
    )
    
    if input_data.assigned_user_id:
        new_job.status = ShippingJobStatus.Assigned
        
    session.add(new_job)
    session.commit()
    session.refresh(new_job)

    log_audit_event(
        session,
        AuditEventType.JOB_CREATED,
        f"Shipping Job {new_job.id} created",
        job_type="shipping_jobs",
        job_id=new_job.id,
    )
    session.commit()

    return new_job

@router.get("/{id}", response_model=ShippingJobOutput)
def get_shipping_job_detail(
    id: int, 
    session: Session = Depends(get_session)
):
    query = select(ShippingJob).where(ShippingJob.id == id).options(
        selectinload(ShippingJob.bins).selectinload(ShippingBin.items).selectinload(Item.barcode),
        selectinload(ShippingJob.bins).selectinload(ShippingBin.non_tray_items).selectinload(NonTrayItem.barcode),
        selectinload(ShippingJob.bins).selectinload(ShippingBin.delivery_location),
        selectinload(ShippingJob.assigned_user)
    )
    job = session.execute(query).scalars().first()
    if not job:
        raise NotFound(detail=f"Shipping Job {id} not found")
    return job

@router.patch("/{id}", response_model=ShippingJobOutput, dependencies=[Depends(RequiresPermission("process_shipping_jobs"))])
def update_shipping_job(
    id: int,
    input_data: ShippingJobUpdateInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Update Job status or assignment.
    """
    check_shipping_enabled(session)
    
    job = session.get(ShippingJob, id)
    if not job:
        raise NotFound(detail=f"Shipping Job {id} not found")
        
    original_status = job.status
    original_assigned_user_id = job.assigned_user_id
    
    # Auto-assign logic
    if input_data.status:
        auto_assign_on_start(job, input_data.status, current_user.id)
        
    if input_data.assigned_user_id is not None and not input_data.status:
        update_status_on_assignment(job, input_data.assigned_user_id, original_status)

    # Apply updates
    data = input_data.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(job, k, v)
        
    # Track transition
    if input_data.status and input_data.status != original_status:
        job.last_transition = datetime.now(timezone.utc)
        
    session.add(job)
    session.commit()
    session.refresh(job)

    target_assigned_user = (
        input_data.assigned_user_id
        if input_data.assigned_user_id is not None
        else getattr(job, "assigned_user_id", None)
    )

    if original_assigned_user_id != target_assigned_user:
        user_msg = "Reassigned" if original_assigned_user_id else "Assigned"
        if target_assigned_user:
            assigned_to_user = session.get(User, target_assigned_user)
            assigned_name = assigned_to_user.first_name + " " + assigned_to_user.last_name if assigned_to_user else str(target_assigned_user)
            log_audit_event(
                session,
                AuditEventType.JOB_ASSIGNED,
                f"Shipping Job {id} {user_msg.lower()} to {assigned_name}",
                job_type="shipping_jobs",
                job_id=id,
            )
        else:
            log_audit_event(
                session,
                AuditEventType.JOB_ASSIGNED,
                f"Shipping Job {id} unassigned",
                job_type="shipping_jobs",
                job_id=id,
            )
        session.commit()

    # Log status change if status was updated
    data = input_data.model_dump(exclude_unset=True)
    new_status_val = data.get("status")
    if new_status_val and new_status_val != original_status:
        log_audit_event(
            session,
            AuditEventType.JOB_STATUS_CHANGED,
            f"Status changed from {original_status} to {new_status_val}",
            job_type="shipping_jobs",
            job_id=id,
        )
        session.commit()

    return job

@router.delete("/{id}", status_code=204, dependencies=[Depends(RequiresPermission("delete_shipping_jobs"))])
def delete_shipping_job(
    id: int,
    session: Session = Depends(get_session)
):
    """
    Delete Shipping Job. Reverts items to Retrieved.
    """
    check_shipping_enabled(session)
    
    job = session.get(ShippingJob, id)
    if not job:
        raise NotFound(detail=f"Shipping Job {id} not found")
        
    if job.status == ShippingJobStatus.Completed:
        raise ValidationException(detail="Cannot delete Completed jobs")
        
    # Get all bins to revert items
    bin_ids = [b.id for b in job.bins]
    
    if bin_ids:
        # Revert items
        session.execute(
            update(Item)
            .where(Item.shipping_bin_id.in_(bin_ids))
            .values(
                status=ItemStatus.Retrieved,
                shipping_bin_id=None,
                scanned_for_shipping=False
            )
        )
        # Revert non-tray items
        session.execute(
            update(NonTrayItem)
            .where(NonTrayItem.shipping_bin_id.in_(bin_ids))
            .values(
                status=NonTrayItemStatus.Retrieved,
                shipping_bin_id=None,
                scanned_for_shipping=False
            )
        )
        
    log_audit_event(
        session,
        AuditEventType.JOB_DELETED,
        f"Shipping Job {id} deleted",
        job_type="shipping_jobs",
        job_id=id,
    )
    session.delete(job) # Cascades to bins
    session.commit()
    
# --- BIN OPERATIONS ---

@router.post("/{id}/bins", response_model=ShippingBinDetailOutput, dependencies=[Depends(RequiresPermission("process_shipping_jobs"))])
def scan_bin(
    id: int,
    barcode: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions)
):
    """
    Scan a bin barcode to create/retrieve it for this job.
    Also handles "auto-clear" logic implicitly if we wanted, but explicit clear is better.
    """
    check_shipping_enabled(session)
    
    job = session.get(ShippingJob, id)
    if not job:
        raise NotFound(detail=f"Job {id} not found")
        
    # Check if bin exists in this job
    existing_bin = session.execute(
        select(ShippingBin).where(
            ShippingBin.shipping_job_id == id,
            ShippingBin.barcode == barcode
        )
    ).scalars().first()
    
    if existing_bin:
        return existing_bin
        
    # Check if this bin barcode is used elsewhere and Uncleared?
    # Logic: "shipping bins are reusable". If it's used in an old job, is it cleared?
    # New requirement: check for UNCLEARED bins with same barcode
    uncleared = session.execute(
        select(ShippingBin).where(
            ShippingBin.barcode == barcode,
            ShippingBin.cleared_dt.is_(None)
        )
    ).scalars().first()
    
    if uncleared:
        raise ValidationException(detail=f"Bin {barcode} is currently active in Job {uncleared.shipping_job_id}")

    # Create new bin
    new_bin = ShippingBin(
        shipping_job_id=id,
        barcode=barcode,
        status=ShippingBinStatus.Open
    )
    session.add(new_bin)
    session.commit()
    session.refresh(new_bin)

    log_audit_event(
        session,
        AuditEventType.BIN_SCANNED,
        f"Bin {barcode} scanned into Shipping Job {id}",
        job_type="shipping_jobs",
        job_id=id,
    )
    session.commit()

    session.refresh(new_bin)
    return new_bin

@router.get("/{id}/items/check", response_model=ShippingItemCheckOutput, dependencies=[Depends(RequiresPermission("process_shipping_jobs"))])
def check_item_for_shipping(
    id: int,
    barcode: str,
    session: Session = Depends(get_session)
):
    """
    Check item delivery location without assigning to bin.
    """
    check_shipping_enabled(session)
    
    # 1. Resolve Barcode
    barcode_obj = session.execute(
        select(Barcode).where(Barcode.value == barcode)
    ).scalars().first()
    
    if not barcode_obj:
        raise NotFound(detail="Barcode not found")
        
    # 2. Find Item or NonTrayItem
    item = session.execute(
        select(Item).where(Item.barcode_id == barcode_obj.id)
    ).scalars().first()
    
    non_tray_item = None
    if not item:
        non_tray_item = session.execute(
            select(NonTrayItem).where(NonTrayItem.barcode_id == barcode_obj.id)
        ).scalars().first()
    
    if not item and not non_tray_item:
        raise NotFound(detail="Item not found")
        
    # 3. Validate Status (Retrieved)
    status = item.status if item else non_tray_item.status
    if status != (ItemStatus.Retrieved if item else NonTrayItemStatus.Retrieved):
        raise ValidationException(detail=f"Item status is {status}, must be Retrieved")

    # 4. Find Active Request
    from app.models.requests import Request, RequestStatus
    
    if item:
        query = select(Request).where(Request.item_id == item.id)
    else:
        query = select(Request).where(Request.non_tray_item_id == non_tray_item.id)
        
    request = session.execute(
        query.where(Request.status != RequestStatus.Completed)
        .order_by(Request.create_dt.desc())
        .options(selectinload(Request.delivery_location))
    ).scalars().first()
    
    if not request:
        raise ValidationException(detail="No active request found for this item.")
         
    if not request.delivery_location_id:
        raise ValidationException(detail="Item's request has no delivery location assigned.")

    return ShippingItemCheckOutput(
        delivery_location_id=request.delivery_location_id,
        delivery_location=request.delivery_location,
        request_id=request.id,
        item_id=item.id if item else None,
        non_tray_item_id=non_tray_item.id if non_tray_item else None
    )

@router.post("/{id}/bins/{bin_id}/items", response_model=ShippingBinDetailOutput, dependencies=[Depends(RequiresPermission("process_shipping_jobs"))])
def scan_item_into_bin(
    id: int,
    bin_id: int,
    item_barcode: str,
    session: Session = Depends(get_session)
):
    """
    Scan an item into a shipping bin.
    """
    check_shipping_enabled(session)
    
    # Get Bin
    bin_obj = session.get(ShippingBin, bin_id)
    if not bin_obj or bin_obj.shipping_job_id != id:
        raise NotFound(detail="Bin not found in this job")
        
    if bin_obj.status == ShippingBinStatus.Closed:
        raise ValidationException(detail="Bin is closed")

    # Resolve Barcode
    barcode_obj = session.execute(
        select(Barcode).where(Barcode.value == item_barcode)
    ).scalars().first()
    
    if not barcode_obj:
        raise NotFound(detail="Barcode not found")
        
    # Find Item or NonTrayItem
    item = session.execute(
        select(Item).where(Item.barcode_id == barcode_obj.id)
    ).scalars().first()
    
    non_tray_item = None
    if not item:
        non_tray_item = session.execute(
            select(NonTrayItem).where(NonTrayItem.barcode_id == barcode_obj.id)
        ).scalars().first()
    
    if not item and not non_tray_item:
        raise NotFound(detail="Item not found")
        
    # Validate Status
    status = item.status if item else non_tray_item.status
    if status != (ItemStatus.Retrieved if item else NonTrayItemStatus.Retrieved):
        raise ValidationException(detail=f"Item status is {status}, must be Retrieved")
        
    # Check current bin
    current_item_bin_id = item.shipping_bin_id if item else non_tray_item.shipping_bin_id
    if current_item_bin_id:
        existing_bin = session.get(ShippingBin, current_item_bin_id)
        if existing_bin and existing_bin.cleared_dt is None:
            existing_job = session.get(ShippingJob, existing_bin.shipping_job_id)
            if existing_job and existing_job.status != ShippingJobStatus.Completed:
                raise ValidationException(detail="Item already in a shipping bin")
        
        # Clean up stale association
        if item:
            item.shipping_bin_id = None
            item.scanned_for_shipping = False
        else:
            non_tray_item.shipping_bin_id = None
            non_tray_item.scanned_for_shipping = False

    # Find Active Request
    from app.models.requests import Request, RequestStatus
    
    if item:
        query = select(Request).where(Request.item_id == item.id)
    else:
        query = select(Request).where(Request.non_tray_item_id == non_tray_item.id)
        
    request = session.execute(
        query.where(Request.status != RequestStatus.Completed)
        .order_by(Request.create_dt.desc())
    ).scalars().first()
    
    if not request:
        raise ValidationException(detail="No active request found for this item.")
         
    item_loc_id = request.delivery_location_id if request else None
    
    if not item_loc_id:
        raise ValidationException(detail="Item's request has no delivery location assigned.")

    # Bin Logic
    if bin_obj.delivery_location_id:
        if item_loc_id and bin_obj.delivery_location_id != item_loc_id:
             bin_loc = session.get(DeliveryLocation, bin_obj.delivery_location_id)
             item_loc = session.get(DeliveryLocation, item_loc_id)
             raise ValidationException(
                 detail=f"Location Mismatch: Item is for {item_loc.name}, Bin is for {bin_loc.name}"
             )
    else:
        if item_loc_id:
            bin_obj.delivery_location_id = item_loc_id
            
    # Add Item to Bin
    if item:
        item.shipping_bin_id = bin_obj.id
        item.scanned_for_shipping = True
        session.add(item)
    else:
        non_tray_item.shipping_bin_id = bin_obj.id
        non_tray_item.scanned_for_shipping = True
        session.add(non_tray_item)
    session.add(bin_obj)
    session.commit()

    entity_id = item.id if item else non_tray_item.id
    log_audit_event(
        session,
        AuditEventType.ITEM_SCANNED,
        f"Item {item_barcode} scanned into Bin {bin_obj.barcode}",
        job_type="shipping_jobs",
        job_id=id,
        entity_type="items" if item else "non_tray_items",
        entity_id=entity_id,
    )
    session.commit()

    # Re-query bin with delivery_location eagerly loaded
    bin_query = select(ShippingBin).where(ShippingBin.id == bin_obj.id).options(
        selectinload(ShippingBin.items).selectinload(Item.barcode),
        selectinload(ShippingBin.non_tray_items).selectinload(NonTrayItem.barcode),
        selectinload(ShippingBin.delivery_location)
    )
    bin_obj = session.execute(bin_query).scalars().first()
    return bin_obj

@router.delete("/{id}/bins/{bin_id}/items/{item_id}", dependencies=[Depends(RequiresPermission("process_shipping_jobs"))])
def remove_item_from_bin(
    id: int,
    bin_id: int,
    item_id: int,
    item_type: str = Query("item", enum=["item", "non_tray_item"]),
    session: Session = Depends(get_session)
):
    check_shipping_enabled(session)
    
    if item_type == "item":
        item = session.get(Item, item_id)
        if not item or item.shipping_bin_id != bin_id:
            raise NotFound(detail="Item not found in this bin")
        item.shipping_bin_id = None
        item.scanned_for_shipping = False
        session.add(item)
    else:
        item = session.get(NonTrayItem, item_id)
        if not item or item.shipping_bin_id != bin_id:
            raise NotFound(detail="Item not found in this bin")
        item.shipping_bin_id = None
        item.scanned_for_shipping = False
        session.add(item)
    
    session.commit()

    log_audit_event(
        session,
        AuditEventType.ITEM_REMOVED,
        f"Item {item_id} ({item_type}) removed from Bin {bin_id}",
        job_type="shipping_jobs",
        job_id=id,
        entity_type="items" if item_type == "item" else "non_tray_items",
        entity_id=item_id,
    )
    session.commit()

    return {"message": "Item removed"}

@router.patch("/{id}/complete", response_model=ShippingJobOutput, dependencies=[Depends(RequiresPermission("process_shipping_jobs"))])
def complete_shipping_job(
    id: int,
    session: Session = Depends(get_session)
):
    """
    Complete the job.
    1. Mark all items in bins as 'Out'.
    2. Set job status to Completed.
    3. Set completed_dt.
    """
    check_shipping_enabled(session)
    
    job = session.get(ShippingJob, id)
    if not job:
        raise NotFound(detail="Job not found")
        
    if job.status == ShippingJobStatus.Completed:
        raise ValidationException(detail="Job already completed")
        
    # Update Items
    # Get all bin IDs
    bin_ids = [b.id for b in job.bins]
    
    if bin_ids:
        # Get Item IDs
        item_ids = [
            item_id for (item_id,) in session.execute(
                select(Item.id).where(Item.shipping_bin_id.in_(bin_ids))
            ).all()
        ]
        # Get Non-Tray Item IDs
        non_tray_item_ids = [
            nt_id for (nt_id,) in session.execute(
                select(NonTrayItem.id).where(NonTrayItem.shipping_bin_id.in_(bin_ids))
            ).all()
        ]

        # Update Items
        if item_ids:
            session.execute(
                update(Item)
                .where(Item.id.in_(item_ids))
                .values(status=ItemStatus.Out, update_dt=datetime.now(timezone.utc))
            )
        # Update Non-Tray Items
        if non_tray_item_ids:
            session.execute(
                update(NonTrayItem)
                .where(NonTrayItem.id.in_(non_tray_item_ids))
                .values(status=NonTrayItemStatus.Out, update_dt=datetime.now(timezone.utc))
            )

        # Complete associated requests
        from app.models.requests import Request, RequestStatus
        if item_ids:
            session.execute(
                update(Request)
                .where(Request.item_id.in_(item_ids))
                .where(Request.status == RequestStatus.Retrieved)
                .values(status=RequestStatus.Completed, fulfilled=True, update_dt=datetime.now(timezone.utc))
            )
        if non_tray_item_ids:
            session.execute(
                update(Request)
                .where(Request.non_tray_item_id.in_(non_tray_item_ids))
                .where(Request.status == RequestStatus.Retrieved)
                .values(status=RequestStatus.Completed, fulfilled=True, update_dt=datetime.now(timezone.utc))
            )
        
    job.status = ShippingJobStatus.Completed
    job.completed_dt = datetime.now(timezone.utc)
    job.last_transition = datetime.now(timezone.utc)
    
    session.add(job)
    session.commit()
    session.refresh(job)

    log_audit_event(
        session,
        AuditEventType.JOB_COMPLETED,
        f"Shipping Job {id} completed",
        job_type="shipping_jobs",
        job_id=id,
    )
    session.commit()

    return job

@router.post("/bins/clear", dependencies=[Depends(RequiresPermission("process_shipping_jobs"))])
def clear_bin(
    barcode: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions)
):
    """
    Mark a bin as "Cleared" (emptied/returned).
    Finds the most recent Open/Closed bin with this barcode.
    """
    bin_obj = session.execute(
        select(ShippingBin)
        .where(ShippingBin.barcode == barcode)
        .where(ShippingBin.cleared_dt.is_(None))
        .order_by(ShippingBin.create_dt.desc())
    ).scalars().first()
    
    if not bin_obj:
        raise NotFound(detail="Active bin not found")

    # Clear item associations
    session.execute(
        update(Item)
        .where(Item.shipping_bin_id == bin_obj.id)
        .values(shipping_bin_id=None, scanned_for_shipping=False)
    )
    session.execute(
        update(NonTrayItem)
        .where(NonTrayItem.shipping_bin_id == bin_obj.id)
        .values(shipping_bin_id=None, scanned_for_shipping=False)
    )
        
    bin_obj.cleared_dt = datetime.now(timezone.utc)
    bin_obj.cleared_by_id = current_user.id
    
    session.add(bin_obj)
    session.commit()

    log_audit_event(
        session,
        AuditEventType.BIN_CLEARED,
        f"Bin {barcode} cleared",
        job_type="shipping_jobs",
        job_id=bin_obj.shipping_job_id,
    )
    session.commit()

    return {"message": f"Bin {barcode} cleared"}
    
@router.get("/{id}/manifest", response_model=ShippingJobOutput, dependencies=[Depends(RequiresPermission("can_access_shipping"))])
def get_shipping_manifest(
    id: int,
    scope: str = Query("full", enum=["full", "location", "bin"]),
    filter_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """
    Get manifest data. optimized for printing.
    """
    check_shipping_enabled(session)
    
    job = session.get(ShippingJob, id)
    if not job:
        raise NotFound(detail="Job not found")

    # Load Bins and Items and Locations for printing
    query = select(ShippingJob).where(ShippingJob.id == id).options(
        selectinload(ShippingJob.bins).selectinload(ShippingBin.items).selectinload(Item.barcode),
        selectinload(ShippingJob.bins).selectinload(ShippingBin.non_tray_items).selectinload(NonTrayItem.barcode),
        selectinload(ShippingJob.bins).selectinload(ShippingBin.delivery_location)
    )
    
    job = session.execute(query).scalars().first()
    
    # Filter in memory if needed
    if scope == "bin" and filter_id:
        job.bins = [b for b in job.bins if b.id == filter_id]
    elif scope == "location" and filter_id:
         job.bins = [b for b in job.bins if b.delivery_location_id == filter_id]
         
    return job
