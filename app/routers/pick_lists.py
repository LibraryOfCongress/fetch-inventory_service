# /code/app/routers/pick_lists.py - FINAL FIX FOR KEYWORD ARGUMENTS

from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session, selectinload 
from sqlalchemy import select, func, update, and_, delete
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record, remove_record
from app.filter_params import SortParams, JobFilterParams
from app.models.buildings import Building
from app.models.item_retrieval_events import ItemRetrievalEvent
from app.models.items import Item, ItemStatus
from app.models.non_tray_item_retrieval_events import NonTrayItemRetrievalEvent
from app.models.non_tray_items import NonTrayItem, NonTrayItemStatus
from app.models.item_withdrawals import ItemWithdrawal
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.pick_lists import PickList
from app.models.requests import Request
from app.models.tray_withdrawal import TrayWithdrawal
from app.models.trays import Tray
from app.models.users import User
from app.models.withdraw_jobs import WithdrawJob
from app.models.requests import RequestStatus
from app.schemas.pick_lists import (
    PickListInput,
    PickListUpdateInput,
    PickListListOutput,
    PickListDetailOutput,
    PickListUpdateRequestInput,
)
from app.config.exceptions import (
    BadRequest,
    NotFound,
    InternalServerError,
)
from app.sorting import PickListSorter
from app.utilities import get_location, manage_transition, check_batch_completion
from app.helpers.system_setting_helpers import get_setting_value

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.utils.job_assignment import auto_assign_on_start, update_status_on_assignment, validate_assignment_lock
from app.services.audit_service import log_audit_event, AuditEventType

router = APIRouter(
    prefix="/pick-lists",
    tags=["pick lists"],
)


def sort_order_priority(session: Session, pick_list, requests):
    request_data = []
    
    if requests:
        for request in requests:
            if request.item_id:
                item = session.get(Item, request.item_id)
                if not item or not item.tray_id:
                    continue
                tray = session.get(Tray, item.tray_id)

                if not tray:
                    continue

                if not tray.shelf_position:
                    continue

                shelf_position = tray.shelf_position

            elif request.non_tray_item_id:
                non_try_item = session.get(NonTrayItem, request.non_tray_item_id)

                if not non_try_item:
                    continue

                if not non_try_item.shelf_position:
                    continue

                shelf_position = non_try_item.shelf_position

            else:
                continue

            location = get_location(session, shelf_position)

            aisle_priority = (
                location["aisle"].sort_priority or location["aisle"].aisle_number
            )
            ladder_priority = (
                location["ladder"].sort_priority or location["ladder"].ladder_number
            )
            shelf_priority = (
                location["shelf"].sort_priority or location["shelf"].shelf_number
            )

            request_data.append(
                {
                    "request": request,
                    "aisle_priority": aisle_priority,
                    "ladder_priority": ladder_priority,
                    "shelf_priority": shelf_priority,
                }
            )

    sorted_request_data = sorted(
        request_data,
        key=lambda x: (
            x["aisle_priority"],
            x["ladder_priority"],
            x["shelf_priority"],
        ),
    )

    # Extract the sorted request objects
    sorted_requests = [data["request"] for data in sorted_request_data]

    # Separate fulfilled and unfulfilled
    unfulfilled_requests = [req for req in sorted_requests if not req.fulfilled]
    fulfilled_requests = [req for req in sorted_requests if req.fulfilled]

    # Append requests not present in sorted_requests (e.g. without shelf location) at the end
    remaining_requests = [req for req in requests if req not in sorted_requests]
    
    # Update the relationship list in memory (SQLAlchemy tracks this)
    pick_list.requests = unfulfilled_requests + fulfilled_requests + remaining_requests

    return pick_list


@router.get("/", response_model=Page[PickListListOutput], dependencies=[Depends(RequiresPermission("can_access_picklist"))])
def get_pick_list_list(
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get a list of pick lists.
    """
    query = select(PickList).options(
        selectinload(PickList.assigned_user),
        selectinload(PickList.created_by),
        selectinload(PickList.building)
    )

    try:
        if params.queue:
            query = query.where(PickList.status != "Completed")
        if params.building_name:
            building_subquery = select(Building.id).where(
                Building.name.in_(params.building_name)
            ).scalar_subquery()
            query = query.where(PickList.building_id.in_(building_subquery))
        if params.status and len(list(filter(None, params.status))) > 0:
            query = query.where(PickList.status.in_(params.status))
        if params.workflow_id:
            query = query.where(PickList.id == params.workflow_id)
        if params.assigned_user_id:
            query = query.where(PickList.assigned_user_id == params.assigned_user_id)
        if params.assigned_user:
            assigned_user_subquery = select(User.id).where(
                func.concat(User.first_name, " ", User.last_name).in_(
                    params.assigned_user
                )
            ).scalar_subquery()
            query = query.where(PickList.assigned_user_id.in_(assigned_user_subquery))
        if params.created_by_id:
            query = query.where(PickList.created_by_id == params.created_by_id)
        if params.from_dt:
            query = query.where(PickList.create_dt >= params.from_dt)
        if params.to_dt:
            query = query.where(PickList.create_dt <= params.to_dt)

        if sort_params.sort_by:
            sorter = PickListSorter(PickList)
            query = sorter.apply_sorting(query, sort_params)

        return paginate(session, query)

    except IntegrityError as e:
        raise InternalServerError(detail=f"{e}")


@router.get("/{id}", response_model=PickListDetailOutput, dependencies=[Depends(RequiresPermission("can_access_picklist"))])
def get_pick_list_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve pick list details by ID.
    """
    pick_list = session.get(PickList, id)

    if not pick_list:
        raise NotFound(detail=f"Pick List ID {id} Not Found")

    return sort_order_priority(session, pick_list, pick_list.requests)


@router.post("/", response_model=PickListDetailOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_create_picklist_job"))])
def create_pick_list(
    pick_list_input: PickListInput, session: Session = Depends(get_session)
):
    """
    Create a new pick list.
    """
    errored_request_ids = []
    
    # 1. Fetch Requests
    requests = (
        session.execute(select(Request).filter(Request.id.in_(pick_list_input.request_ids)))
        .scalars()
        .all()
    )

    if not requests:
        raise BadRequest(detail="Request Not Found")

    if len(requests) != len(pick_list_input.request_ids):
        errored_request_ids.append(set(pick_list_input.request_ids) - set(req.id for req in requests)) 

    # 2. Update Items Status
    item_ids = [request.item_id for request in requests if request.item_id is not None]
    if item_ids:
        session.execute(
            update(Item)
            .where(Item.id.in_(item_ids))
            .values(status=ItemStatus.PickList)
        )

    non_tray_item_ids = [request.non_tray_item_id for request in requests if request.non_tray_item_id is not None]
    if non_tray_item_ids:
        session.execute(
            update(NonTrayItem)
            .where(NonTrayItem.id.in_(non_tray_item_ids))
            .values(status=NonTrayItemStatus.PickList)
        )

    building_id = requests[0].building_id
    
    # --- CRITICAL FIX: Manually prepare data for PickList constructor ---
    # Convert Pydantic model to dict
    pick_list_data = pick_list_input.model_dump()
    
    # Explicitly remove fields that are not columns in the PickList table
    pick_list_data.pop("request_ids", None)
    pick_list_data.pop("errored_request_ids", None) # Safety check
    
    # Ensure mandatory fields have values if missing from input
    if "last_transition" not in pick_list_data or pick_list_data["last_transition"] is None:
        pick_list_data["last_transition"] = datetime.now(timezone.utc)
    
    # Instantiate
    new_pick_list = PickList(**pick_list_data)
    # ------------------------------------------------------------------
    
    new_pick_list.building = session.get(Building, building_id)
    session.add(new_pick_list)
    session.flush()

    session.execute(
        update(Request)
        .where(Request.id.in_(pick_list_input.request_ids))
        .values(pick_list_id=new_pick_list.id, status=RequestStatus.PickList)
    )

    session.commit()
    session.refresh(new_pick_list)

    log_audit_event(
        session,
        AuditEventType.JOB_CREATED,
        f"Picklist {new_pick_list.id} created with {len(pick_list_input.request_ids)} requests",
        job_type="pick_lists",
        job_id=new_pick_list.id,
    )
    session.commit()

    if errored_request_ids:
        setattr(new_pick_list, "errored_request_ids", errored_request_ids)

    return sort_order_priority(session, new_pick_list, new_pick_list.requests)


@router.patch("/{id}", response_model=PickListDetailOutput, dependencies=[Depends(RequiresPermission("process_pick_lists"))])
def update_pick_list(
    id: int, 
    pick_list: PickListUpdateInput, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Update an existing pick list.
    
    Includes auto-assignment logic:
    - When a user starts a job (status → Running), auto-assign to them if unassigned
    - Prevent users from starting jobs assigned to others
    - When manager assigns a user, auto-update status to Assigned
    """
    try:
        existing_pick_list = session.get(PickList, id)

        if not existing_pick_list:
            raise NotFound(detail=f"Pick List ID {id} Not Found")
        
        # Capture original status and assigned user before changes
        original_status = existing_pick_list.status
        original_assigned_user_id = existing_pick_list.assigned_user_id
        
        # Handle auto-assignment when user starts job
        if pick_list.status:
            auto_assign_on_start(
                existing_pick_list, 
                pick_list.status, 
                current_user.id
            )
        
        # Handle status update when manager assigns user
        if pick_list.assigned_user_id is not None and not pick_list.status:
            update_status_on_assignment(
                existing_pick_list,
                pick_list.assigned_user_id,
                original_status
            )

        items_to_sync = []
        if pick_list.status == "Completed":
            request_ids = [
                request_id
                for (request_id,) in session.execute(
                    select(Request.id).filter(Request.pick_list_id == id)
                ).all()
            ]

            if request_ids:
                item_ids = [
                    item_id
                    for (item_id,) in session.execute(
                        select(Item.id)
                        .join(Request, Item.id == Request.item_id)
                        .filter(Request.id.in_(request_ids))
                    ).all()
                ]
                
                non_tray_item_ids = [
                    non_tray_item_id
                    for (non_tray_item_id,) in session.execute(
                        select(NonTrayItem.id)
                        .join(Request, NonTrayItem.id == Request.non_tray_item_id)
                        .filter(Request.id.in_(request_ids))
                    ).all()
                ]

                # Check shipping module
                shipping_enabled = get_setting_value(session, "shipping_module_enabled", "false")
                target_status = "Retrieved" if shipping_enabled.lower() == "true" else "Out"

                if item_ids:
                    session.execute(
                        update(Item).where(Item.id.in_(item_ids)).values(
                            status=target_status,
                            scanned_for_refile=None,
                            update_dt=datetime.now(timezone.utc),
                        )
                    )

                if non_tray_item_ids:
                    session.execute(
                        update(NonTrayItem).where(NonTrayItem.id.in_(non_tray_item_ids)).values(
                            status=target_status,
                            scanned_for_refile=None,
                            update_dt=datetime.now(timezone.utc),
                        )
                    )

                if shipping_enabled.lower() == "true":
                    # Shipping enabled: keep requests active as Retrieved
                    session.execute(
                        update(Request).where(Request.id.in_(request_ids)).values(
                            status=RequestStatus.Retrieved,
                            fulfilled=False,
                            update_dt=datetime.now(timezone.utc),
                        )
                    )
                else:
                    # Shipping disabled: complete requests immediately
                    session.execute(
                        update(Request).where(Request.id.in_(request_ids)).values(
                            fulfilled=True,
                            status=RequestStatus.Completed,
                            update_dt=datetime.now(timezone.utc),
                        )
                    )

                # Check for batch completion
                batch_ids = (
                    session.execute(
                        select(Request.batch_upload_id)
                        .where(Request.id.in_(request_ids))
                        .where(Request.batch_upload_id.isnot(None))
                        .distinct()
                    )
                    .scalars()
                    .all()
                )

                for batch_id in batch_ids:
                    check_batch_completion(session, batch_id)

                existing_withdraw_job = (
                    session.execute(select(WithdrawJob).filter(WithdrawJob.pick_list_id == id))
                    .scalars()
                    .first()
                )

                if not existing_withdraw_job:
                    if item_ids:
                        items = session.execute(select(Item).filter(Item.id.in_(item_ids))).scalars().all()
                        for item in items:
                            session.add(ItemRetrievalEvent(
                                item_id=item.id,
                                owner_id=item.owner_id,
                                pick_list_id=id,
                            ))
                            if getattr(item, 'barcode', None):
                                items_to_sync.append((item.barcode.value, item.owner_id, False))
                    if non_tray_item_ids:
                        non_tray_items = (
                            session.execute(select(NonTrayItem).filter(NonTrayItem.id.in_(non_tray_item_ids)))
                            .scalars()
                            .all()
                        )
                        for non_tray_item in non_tray_items:
                            session.add(NonTrayItemRetrievalEvent(
                                non_tray_item_id=non_tray_item.id,
                                owner_id=non_tray_item.owner_id,
                                pick_list_id=id,
                            ))
                            if getattr(non_tray_item, 'barcode', None):
                                items_to_sync.append((non_tray_item.barcode.value, non_tray_item.owner_id, True))

        if pick_list.status and pick_list.run_timestamp:
            existing_pick_list = manage_transition(existing_pick_list, pick_list)

        mutated_data = pick_list.model_dump(
            exclude_unset=True, exclude={"run_timestamp"}
        )

        for key, value in mutated_data.items():
            setattr(existing_pick_list, key, value)

        setattr(existing_pick_list, "update_dt", datetime.now(timezone.utc))

        session.add(existing_pick_list)
        session.commit()
        session.refresh(existing_pick_list)

        # Log status change if status was updated
        mutated_data = pick_list.model_dump(exclude_unset=True, exclude={"run_timestamp"})
        new_status_val = mutated_data.get("status")
        if new_status_val and new_status_val != original_status:
            log_audit_event(
                session,
                AuditEventType.JOB_STATUS_CHANGED,
                f"Status changed from {original_status} to {new_status_val}",
                job_type="pick_lists",
                job_id=id,
            )
            session.commit()

        target_assigned_user = (
            pick_list.assigned_user_id
            if pick_list.assigned_user_id is not None
            else getattr(existing_pick_list, "assigned_user_id", None)
        )

        if original_assigned_user_id != target_assigned_user:
            user_msg = "Reassigned" if original_assigned_user_id else "Assigned"
            if target_assigned_user:
                assigned_to_user = session.get(User, target_assigned_user)
                assigned_name = assigned_to_user.first_name + " " + assigned_to_user.last_name if assigned_to_user else str(target_assigned_user)
                log_audit_event(
                    session,
                    AuditEventType.JOB_ASSIGNED,
                    f"Picklist {id} {user_msg.lower()} to {assigned_name}",
                    job_type="pick_lists",
                    job_id=id,
                )
            else:
                log_audit_event(
                    session,
                    AuditEventType.JOB_ASSIGNED,
                    f"Picklist {id} unassigned",
                    job_type="pick_lists",
                    job_id=id,
                )
            session.commit()
            
        if pick_list.status == "Completed" and items_to_sync:
            from app.ils.tasks import check_in_picklist_item_async
            for barcode_value, owner_id, is_non_tray in items_to_sync:
                check_in_picklist_item_async(
                    barcode_value=barcode_value,
                    owner_id=owner_id,
                    is_non_tray=is_non_tray,
                    pick_list_id=id
                )

        return sort_order_priority(
            session, existing_pick_list, existing_pick_list.requests
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{pick_list_id}/add_request", response_model=PickListDetailOutput, dependencies=[Depends(RequiresPermission("process_pick_lists"))])
def add_request_to_pick_list(
    pick_list_id: int,
    pick_list_input: PickListInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Add a request to an existing pick list.
    """
    if not pick_list_id:
        raise BadRequest(detail="Pick List ID Not Found")

    pick_list = session.get(PickList, pick_list_id)
    
    if pick_list:
        validate_assignment_lock(pick_list, current_user.id)
    update_dt = datetime.now(timezone.utc)
    errored_request_ids = []

    if pick_list.status in ["Running", "Completed"]:
        raise BadRequest(
            detail="Can not add request to 'Running' or 'Completed' Pick List"
        )

    if not pick_list:
        raise NotFound(detail=f"Pick List ID {pick_list_id} Not Found")

    if not pick_list_input.request_ids:
        raise BadRequest(detail="Request IDs Not Found")

    existing_requests = session.execute(
        select(Request).where(Request.id.in_(pick_list_input.request_ids))
    ).scalars().all()

    if len(existing_requests) != len(pick_list_input.request_ids):
        errored_request_ids.append(
            set(pick_list_input.request_ids) - set(req.id for req in existing_requests)
        )

    session.execute(
        update(Request).where(Request.id.in_(pick_list_input.request_ids)).values(
            pick_list_id=pick_list_id,
            status=RequestStatus.PickList,
            update_dt=datetime.now(timezone.utc),
        )
    )

    if not pick_list.building_id:
        pick_list.building_id = existing_requests[0].building_id

    item_ids = [request.item_id for request in existing_requests if request.item_id is not None]
    if item_ids:
        session.execute(
            update(Item).where(Item.id.in_(item_ids)).values(status=ItemStatus.PickList)
        )

    non_tray_item_ids = [request.non_tray_item_id for request in existing_requests if request.non_tray_item_id is not None]
    if non_tray_item_ids:
        session.execute(
            update(NonTrayItem).where(NonTrayItem.id.in_(non_tray_item_ids)).values(status=NonTrayItemStatus.PickList)
        )

    pick_list.update_dt = update_dt

    session.commit()
    session.refresh(pick_list)

    for req in existing_requests:
        log_audit_event(
            session,
            AuditEventType.REQUEST_ADDED,
            f"Request {req.id} added to Picklist {pick_list_id}",
            job_type="pick_lists",
            job_id=pick_list_id,
            entity_type="items" if req.item_id else "non_tray_items",
            entity_id=req.item_id or req.non_tray_item_id,
        )
    session.commit()

    if errored_request_ids:
        setattr(pick_list, "errored_request_ids", errored_request_ids)

    return sort_order_priority(session, pick_list, pick_list.requests)


@router.patch(
    "/{pick_list_id}/update_request/{request_id}", response_model=PickListDetailOutput, dependencies=[Depends(RequiresPermission("process_pick_lists"))]
)
def update_request_for_pick_list(
    pick_list_id: int,
    request_id: int,
    pick_list_request_input: PickListUpdateRequestInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Update a request for an existing pick list.
    """
    existing_pick_list = (
        session.execute(
            select(PickList)
            .filter(PickList.id == pick_list_id)
            .filter(PickList.requests.any(Request.id == request_id))
        )
        .scalars()
        .first()
    )
    update_dt = datetime.now(timezone.utc)

    if not existing_pick_list:
        raise NotFound(
            detail=f"Pick List ID {pick_list_id} or Request ID {request_id} Not Found"
        )
        
    validate_assignment_lock(existing_pick_list, current_user.id)

    existing_pick_list.update_dt = update_dt
    
    session.execute(
        update(Request).where(Request.id == request_id).values(
            fulfilled=True,
            update_dt=update_dt
        )
    )

    if pick_list_request_input.status:
        request = session.get(Request, request_id)
        if request.item:
            session.execute(
                update(Item).where(Item.id == request.item.id).values(
                    status=pick_list_request_input.status,
                    update_dt=datetime.now(timezone.utc)
                )
            )

        else:
            session.execute(
                update(NonTrayItem).where(NonTrayItem.id == request.non_tray_item.id).values(
                    status=pick_list_request_input.status,
                    update_dt=datetime.now(timezone.utc)
                )
            )

    session.commit()
    session.refresh(existing_pick_list)

    # Get human readable barcode
    barcode_value = str(request_id)
    if request.item and request.item.barcode:
        barcode_value = request.item.barcode.value
    elif request.non_tray_item and request.non_tray_item.barcode:
        barcode_value = request.non_tray_item.barcode.value

    log_audit_event(
        session,
        AuditEventType.ITEM_PICKED,
        f"Barcode # {barcode_value} retrieved",
        job_type="pick_lists",
        job_id=pick_list_id,
    )
    session.commit()

    # Check for batch completion for the single request
    request = session.get(Request, request_id)
    if request and request.batch_upload_id:
        check_batch_completion(session, request.batch_upload_id)

    return sort_order_priority(session, existing_pick_list, existing_pick_list.requests)


@router.delete(
    "/{pick_list_id}/remove_request/{request_id}", response_model=PickListDetailOutput, dependencies=[Depends(RequiresPermission("process_pick_lists"))]
)
def remove_request_from_pick_list(
    pick_list_id: int, 
    request_id: int, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Remove a request from an existing pick list.
    """
    pick_list = session.get(PickList, pick_list_id)
    update_dt = datetime.now(timezone.utc)

    if not pick_list:
        raise NotFound(detail=f"Pick List ID {pick_list_id} Not Found")
        
    validate_assignment_lock(pick_list, current_user.id)

    if pick_list.status == "Completed":
        raise BadRequest(detail="Pick List Already Completed")

    request = session.get(Request, request_id)

    if not request:
        raise NotFound(detail=f"Request ID {request_id} Not Found")

    session.execute(
        update(Request).where(Request.id == request_id).values(
            pick_list_id=None,
            status=RequestStatus.New,
            fulfilled=False,
            update_dt=update_dt
        )
    )

    existing_withdraw_job = session.execute(
        select(WithdrawJob).where(WithdrawJob.pick_list_id == pick_list_id)
    ).scalars().first()

    if request.item:
        session.execute(
            update(Item).where(Item.id == request.item.id).values(status=ItemStatus.Requested, update_dt=update_dt)
        )

        if existing_withdraw_job:
            session.execute(
                delete(ItemWithdrawal)
                .where(ItemWithdrawal.item_id == request.item.id,
                       ItemWithdrawal.withdraw_job_id == existing_withdraw_job.id)
            )

            item_withdrawals = (
                session.execute(
                    select(ItemWithdrawal)
                    .filter(ItemWithdrawal.withdraw_job_id == existing_withdraw_job.id)
                )
                .scalars()
                .all()
            )

            if not item_withdrawals:
                session.execute(
                    delete(TrayWithdrawal)
                    .where(TrayWithdrawal.withdraw_job_id == existing_withdraw_job.id,
                           TrayWithdrawal.tray_id == request.item.tray_id)
                )

    else:
        session.execute(
            update(NonTrayItem).where(NonTrayItem.id == request.non_tray_item.id).values(
                status=NonTrayItemStatus.Requested, update_dt=update_dt
            )
        )

        if existing_withdraw_job:
            session.execute(
                delete(NonTrayItemWithdrawal)
                .where(NonTrayItemWithdrawal.non_tray_item_id == request.non_tray_item.id,
                       NonTrayItemWithdrawal.withdraw_job_id == existing_withdraw_job.id)
            )

    setattr(pick_list, "update_dt", update_dt)

    session.commit()
    session.refresh(pick_list)

    log_audit_event(
        session,
        AuditEventType.REQUEST_REMOVED,
        f"Request {request_id} removed from Picklist {pick_list_id}",
        job_type="pick_lists",
        job_id=pick_list_id,
    )
    session.commit()

    return sort_order_priority(session, pick_list, pick_list.requests)


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_delete_picklist_job"))])
def delete_pick_list(id: int, session: Session = Depends(get_session)):
    """
    Delete an existing pick list.
    """
    pick_list = session.get(PickList, id)

    if not pick_list:
        raise NotFound(detail=f"Pick List ID {id} Not Found")

    requests = pick_list.requests

    item_ids = [request.item_id for request in requests if request.item_id is not None]
    non_tray_item_ids = [request.non_tray_item_id for request in requests if request.non_tray_item_id is not None]

    if item_ids:
        session.execute(
            update(Item).where(Item.id.in_(item_ids)).values(
                status=ItemStatus.Requested, update_dt=datetime.now(timezone.utc)
            )
        )

    if non_tray_item_ids:
        session.execute(
            update(NonTrayItem).where(NonTrayItem.id.in_(non_tray_item_ids)).values(
                status=NonTrayItemStatus.Requested, update_dt=datetime.now(timezone.utc)
            )
        )

    if requests:
        session.execute(
            update(Request).where(Request.id.in_([r.id for r in requests])).values(
                pick_list_id=None,
                status=RequestStatus.New,
                fulfilled=False,
                update_dt=datetime.now(timezone.utc),
            )
        )

    session.execute(
        update(WithdrawJob).where(WithdrawJob.pick_list_id == id).values(
            pick_list_id=None, update_dt=datetime.now(timezone.utc)
        )
    )

    log_audit_event(
        session,
        AuditEventType.JOB_DELETED,
        f"Picklist {id} deleted",
        job_type="pick_lists",
        job_id=id,
    )
    session.delete(pick_list)
    session.commit()

    raise HTTPException(
        status_code=204, detail=f"Pick list ID {id} Deleted Successfully"
    )