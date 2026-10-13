# /code/app/routers/withdraw_jobs.py - FINAL FIX (EXCLUDE BARCODE_VALUE)

from datetime import datetime, timezone
from typing import List

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session
from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from starlette.responses import JSONResponse

from app.database.session import get_session, commit_record
from app.filter_params import SortParams, JobFilterParams
from app.logger import inventory_logger
from app.models.barcodes import Barcode
from app.models.batch_upload import BatchUpload
from app.models.item_withdrawals import ItemWithdrawal
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.tray_withdrawal import TrayWithdrawal
from app.models.trays import Tray
from app.models.users import User
from app.models.withdraw_jobs import WithdrawJob
from app.models.pick_lists import PickList
from app.models.requests import Request
from app.sorting import WithdrawJobSorter
from app.utilities import (
    validate_item_not_shelved,
    validate_container_not_shelved, start_session_with_audit_info,
)
from app.events import update_shelf_space_after_non_tray, update_shelf_space_after_tray
from starlette import status
from app.schemas.withdraw_jobs import (
    WithdrawJobInput,
    WithdrawJobWriteOutput,
    WithdrawJobUpdateInput,
    WithdrawJobListOutput,
    WithdrawJobDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    BadRequest,
    ValidationException,
    InternalServerError,
)
from app.utilities import manage_transition, get_module_shelf_position
from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.utils.job_assignment import auto_assign_on_start, update_status_on_assignment
from app.services.audit_service import log_audit_event, AuditEventType

router = APIRouter(
    prefix="/withdraw-jobs",
    tags=["withdraw jobs"],
    dependencies=[Depends(RequiresPermission("can_access_withdraw"))],
)


ShelfBarcodeAlias = aliased(Barcode)
TrayBarcodeAlias = aliased(Barcode)


def validate_withdraw_item(items: List[ItemWithdrawal | NonTrayItemWithdrawal], job_id, status, session: Session):
    if not items:
        return False

    existing_withdraw_ids = {
        item.withdraw_job_id for item in items if hasattr(item, 'withdraw_job_id')
    }
    
    existing_withdraws = (
        session.execute(
            select(WithdrawJob.id, WithdrawJob.status)
            .filter(WithdrawJob.id.in_(existing_withdraw_ids))
        )
        .all()
    )

    return any(
        item.id == job_id or item.status != status for item in existing_withdraws
    )


@router.get("/", response_model=Page[WithdrawJobListOutput])
def get_withdraw_job_list(
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of withdraw jobs.
    """
    query = select(WithdrawJob)

    if params.queue:
        query = query.where(
            WithdrawJob.status != "Completed"
        )
    if params.status and len(list(filter(None, params.status))) > 0:
        query = query.where(WithdrawJob.status.in_(params.status))
    if params.workflow_id:
        query = query.where(WithdrawJob.id == params.workflow_id)
    if params.assigned_user_id:
        query = query.where(WithdrawJob.assigned_user_id == params.assigned_user_id)
    if params.assigned_user:
        assigned_user_subquery = (
            select(User.id)
            .where(
                func.concat(User.first_name, ' ', User.last_name).in_(
                    params.assigned_user
                )
            )
            .distinct().scalar_subquery()
        )
        query = query.where(WithdrawJob.assigned_user_id.in_(assigned_user_subquery))
    if params.created_by_id:
        query = query.where(WithdrawJob.created_by_id == params.created_by_id)
    if params.from_dt:
        query = query.where(WithdrawJob.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(WithdrawJob.create_dt <= params.to_dt)


    if sort_params.sort_by:
        sorter = WithdrawJobSorter(WithdrawJob)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=WithdrawJobDetailOutput)
def get_withdraw_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a withdraw job from the database using the provided ID.
    """
    withdraw_job = session.get(WithdrawJob, id)

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {id} not found")

    return withdraw_job


@router.post("/", response_model=WithdrawJobWriteOutput)
def create_withdraw_job(
    withdraw_job_input: WithdrawJobInput, session: Session = Depends(get_session)
) -> WithdrawJob:
    """
    Creates a new withdraw job in the database.
    """
    # CRITICAL FIX: Exclude 'barcode_value' from the model dump
    new_withdraw_job = WithdrawJob(**withdraw_job_input.model_dump(exclude={"barcode_value"}))

    session.add(new_withdraw_job)
    session.commit()
    session.refresh(new_withdraw_job)

    log_audit_event(
        session,
        AuditEventType.JOB_CREATED,
        f"Withdrawal Job {new_withdraw_job.id} created",
        job_type="withdraw_jobs",
        job_id=new_withdraw_job.id,
    )
    session.commit()

    return new_withdraw_job


@router.patch("/{id}", response_model=WithdrawJobDetailOutput)
def update_withdraw_job(
    id: int,
    withdraw_job_input: WithdrawJobUpdateInput,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions),
):
    """
    Updates an existing withdraw job in the database.
    
    Includes auto-assignment logic:
    - When a user starts a job (status → Running), auto-assign to them if unassigned
    - Prevent users from starting jobs assigned to others
    - When manager assigns a user, auto-update status to Assigned
    """

    existing_withdraw_job = session.get(WithdrawJob, id)

    if not existing_withdraw_job:
        raise NotFound(detail=f"Withdraw job id {id} not found")
    
    # Capture original status before changes
    original_status = existing_withdraw_job.status
    original_assigned_user_id = existing_withdraw_job.assigned_user_id
    
    # Handle auto-assignment when user starts job
    if withdraw_job_input.status:
        auto_assign_on_start(
            existing_withdraw_job, 
            withdraw_job_input.status, 
            current_user.id
        )
    
    # Handle status update when manager assigns user
    if withdraw_job_input.assigned_user_id is not None and not withdraw_job_input.status:
        update_status_on_assignment(
            existing_withdraw_job,
            withdraw_job_input.assigned_user_id,
            original_status
        )

    updated_dt = datetime.now(timezone.utc)

    pick_list = None
    building_id = None
    new_request = []
    audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
    if withdraw_job_input.create_pick_list or withdraw_job_input.add_to_picklist:
        if withdraw_job_input.create_pick_list:
            if existing_withdraw_job.pick_list_id:
                pick_list = session.get(PickList, existing_withdraw_job.pick_list_id)
                if not pick_list:
                    raise NotFound(
                        detail=f"Pick list id {existing_withdraw_job.pick_list_id} not found"
                    )
                if pick_list.status == "Completed":
                    raise BadRequest(detail="Pick List Already Completed")
            else:
                pick_list = PickList(
                    create_dt=updated_dt,
                    update_dt=updated_dt,
                    last_transition=updated_dt,
                )
                session.add(pick_list)
                session.commit()
                session.refresh(pick_list)
                # Set the pick_list_id on the withdraw job
                existing_withdraw_job.pick_list_id = pick_list.id
                session.commit()

        elif withdraw_job_input.add_to_picklist:
            pick_list = session.get(PickList, existing_withdraw_job.pick_list_id)
            if not pick_list:
                raise NotFound(
                    detail=f"Pick list id {withdraw_job_input.pick_list_id} not found"
                )

            if pick_list.status == "Completed":
                raise BadRequest(detail="Pick List Already Completed")

        item_ids = []
        non_tray_item_ids = []

        for item in existing_withdraw_job.items:
            if not building_id:
                tray = session.get(Tray, item.tray_id)
                module = get_module_shelf_position(session, tray.shelf_position)
                building_id = module.building_id

                pick_list.building_id = building_id
                pick_list.status = "Created"
                session.add(pick_list)
                start_session_with_audit_info(audit_info, session)
                session.commit()
                session.refresh(pick_list)

            if item.status == "In":
                new_request.append(
                    Request(
                        building_id=building_id,
                        item_id=item.id,
                        pick_list_id=pick_list.id,
                    )
                )
                item_ids.append(item.id)
            if item.status == "Requested":
                session.execute(
                    update(Request).filter(
                        Request.item_id == item.id,
                        Request.pick_list_id == None,
                        Request.fulfilled == False,
                    ).values(pick_list_id=pick_list.id, update_dt=updated_dt)
                )

        for non_tray_item in existing_withdraw_job.non_tray_items:
            if not building_id:
                module = get_module_shelf_position(
                    session, non_tray_item.shelf_position
                )
                building_id = module.building_id
                pick_list.building_id = building_id
                session.add(pick_list)
                start_session_with_audit_info(audit_info, session)
                session.commit()
                session.refresh(pick_list)

            if non_tray_item.status == "In":
                new_request.append(
                    Request(
                        building_id=building_id,
                        non_tray_item_id=non_tray_item.id,
                        pick_list_id=pick_list.id,
                    )
                )
                non_tray_item_ids.append(non_tray_item.id)

            if non_tray_item.status == "Requested":
                session.execute(
                    update(Request).filter(
                        Request.non_tray_item_id == non_tray_item.id,
                        Request.pick_list_id == None,
                        Request.fulfilled == False,
                    ).values(pick_list_id=pick_list.id, update_dt=updated_dt)
                )

        if new_request:
            session.bulk_save_objects(new_request)
            start_session_with_audit_info(audit_info, session)
            session.commit()

        session.execute(
            update(Item).filter(Item.id.in_(item_ids)).values(status="PickList", update_dt=updated_dt)
        )
        session.execute(
            update(NonTrayItem).filter(NonTrayItem.id.in_(non_tray_item_ids)).values(status="PickList", update_dt=updated_dt)
        )
        session.execute(
            update(WithdrawJob).filter(WithdrawJob.id == id).values(pick_list_id=pick_list.id)
        )

    if withdraw_job_input.status == "Completed":
        tray_ids = [item.tray_id for item in existing_withdraw_job.items]
        item_ids = [item.id for item in existing_withdraw_job.items]
        item_barcodes = [item.barcode_id for item in existing_withdraw_job.items]
        non_tray_item_ids = [
            non_tray_item.id for non_tray_item in existing_withdraw_job.non_tray_items
        ]
        non_tray_item_barcodes = [
            non_tray_item.barcode_id
            for non_tray_item in existing_withdraw_job.non_tray_items
        ]
        if item_ids:
            # Updating items status to withdrawn
            items_to_update = session.execute(
                select(
                    Item.id,
                    Item.barcode_id,
                    ShelfPosition,
                    ShelfBarcodeAlias.value.label("shelf_barcode_value"),
                    TrayBarcodeAlias.value.label("tray_barcode_value"),
                                ).select_from(Item).join(
                    Tray, Item.tray_id == Tray.id
                ).join(
                    ShelfPosition, Tray.shelf_position_id == ShelfPosition.id
                ).join(
                    Shelf, ShelfPosition.shelf_id == Shelf.id
                ).outerjoin(
                    ShelfBarcodeAlias, Shelf.barcode_id == ShelfBarcodeAlias.id
                ).outerjoin(
                    TrayBarcodeAlias, Tray.barcode_id == TrayBarcodeAlias.id
                ).filter(
                    Item.id.in_(item_ids)
                )
            ).all()

            for (
                item_id,
                barcode_id,
                shelf_position,
                shelf_barcode_value,
                tray_barcode_value,
            ) in items_to_update:
                location = shelf_position.location if shelf_position else None
                internal_location = shelf_position.internal_location if shelf_position else None
                session.execute(update(Item).filter(Item.id == item_id).values(
                    withdrawal_dt=updated_dt,
                    withdrawn_barcode_id=barcode_id,
                    withdrawn_location=location,
                    withdrawn_internal_location=internal_location,
                    withdrawn_loc_bcodes=f"{shelf_barcode_value}-{tray_barcode_value}",
                    barcode_id=None,
                    update_dt=updated_dt,
                    status="Withdrawn",
                    tray_id=None,
                ))

            session.execute(
                update(Barcode).filter(Barcode.id.in_(item_barcodes)).values(
                    withdrawn=True, update_dt=updated_dt
                )
            )
            
            start_session_with_audit_info(audit_info, session)
            session.commit()

            if tray_ids:
                trays = session.execute(select(Tray).filter(Tray.id.in_(tray_ids))).scalars().all()
                empty_trays = [tray for tray in trays if len(tray.items) == 0]

                if empty_trays:
                    tray_barcode_ids = [tray.barcode_id for tray in empty_trays]
                    
                    session.execute(
                        update(Barcode).filter(Barcode.id.in_(tray_barcode_ids)).values(
                            withdrawn=True, update_dt=updated_dt
                        )
                    )

                    trays_to_update = session.execute(
                        select(
                            Tray.id,
                            Tray.barcode_id,
                            Tray.shelf_position_id,
                            ShelfPosition,
                            ShelfBarcodeAlias.value.label("shelf_barcode_value"),
                            TrayBarcodeAlias.value.label("tray_barcode_value"),
                                                ).select_from(Tray).join(
                            ShelfPosition, Tray.shelf_position_id == ShelfPosition.id
                        ).join(
                            Shelf, ShelfPosition.shelf_id == Shelf.id
                        ).outerjoin(
                            ShelfBarcodeAlias, Shelf.barcode_id == ShelfBarcodeAlias.id
                        ).outerjoin(
                            TrayBarcodeAlias, Tray.barcode_id == TrayBarcodeAlias.id
                        ).filter(
                            Tray.id.in_(tray_ids)
                        )
                    ).all()

                    for (
                        tray_id,
                        barcode_id,
                        shelf_position_id,
                        shelf_position,
                        shelf_barcode_value,
                        tray_barcode_value,
                    ) in trays_to_update:
                        location = shelf_position.location if shelf_position else None
                        internal_location = shelf_position.internal_location if shelf_position else None
                        session.execute(update(Tray).filter(Tray.id == tray_id).values(
                            shelf_position_id=None,
                            shelf_position_proposed_id=None,
                            withdrawn_barcode_id=barcode_id,
                            withdrawn_location=location,
                            withdrawn_internal_location=internal_location,
                            withdrawn_loc_bcodes=f"{shelf_barcode_value}-{tray_barcode_value}",
                            barcode_id=None,
                            withdrawal_dt=updated_dt,
                            update_dt=updated_dt,
                        ))
                    for tray in trays_to_update:
                        update_shelf_space_after_tray(session, tray, tray.shelf_position_id, None)

        if non_tray_item_ids:
            non_tray_items_to_update = session.execute(
                select(
                    NonTrayItem.id,
                    NonTrayItem.barcode_id,
                    NonTrayItem.shelf_position_id,
                    ShelfPosition,
                    ShelfBarcodeAlias.value.label("shelf_barcode_value"),
                                ).select_from(NonTrayItem).join(
                    ShelfPosition, ShelfPosition.id == NonTrayItem.shelf_position_id
                ).join(
                    Shelf, Shelf.id == ShelfPosition.shelf_id
                ).outerjoin(
                    ShelfBarcodeAlias, ShelfBarcodeAlias.id == Shelf.barcode_id
                ).filter(
                    NonTrayItem.id.in_(non_tray_item_ids)
                )
            ).all()

            for (
                item_id,
                barcode_id,
                shelf_position_id,
                shelf_position,
                shelf_barcode_value
            ) in non_tray_items_to_update:
                location = shelf_position.location if shelf_position else None
                internal_location = shelf_position.internal_location if shelf_position else None
                session.execute(update(NonTrayItem).filter(NonTrayItem.id == item_id).values(
                    withdrawal_dt=updated_dt,
                    withdrawn_barcode_id=barcode_id,
                    withdrawn_location=location,
                    withdrawn_internal_location=internal_location,
                    withdrawn_loc_bcodes=f"{shelf_barcode_value}",
                    barcode_id=None,
                    update_dt=updated_dt,
                    status="Withdrawn",
                    shelf_position_id=None,
                    shelf_position_proposed_id=None,
                ))
            non_tray_item_barcodes = [row.barcode_id for row in non_tray_items_to_update]
            # Store shelf_position_ids before updating (they get set to None in the update)
            shelf_position_ids_to_update = [row.shelf_position_id for row in non_tray_items_to_update]
            
            session.execute(
                update(Barcode).filter(Barcode.id.in_(non_tray_item_barcodes)).values(
                    withdrawn=True, update_dt=updated_dt
                )
            )
            # Update shelf space using the saved shelf_position_ids
            for shelf_position_id in shelf_position_ids_to_update:
                if shelf_position_id:
                    update_shelf_space_after_non_tray(session, None, None, shelf_position_id)

    if withdraw_job_input.status:
        if withdraw_job_input.run_timestamp:
            existing_withdraw_job = manage_transition(
                existing_withdraw_job, withdraw_job_input
            )
        else:
            session.execute(
                update(WithdrawJob).filter(
                    WithdrawJob.id == id
                ).values(last_transition=updated_dt)
            )

    mutated_data = withdraw_job_input.model_dump(
        exclude_unset=True,
        exclude={"run_timestamp", "create_pick_list", "add_to_picklist"},
    )

    for key, value in mutated_data.items():
       if withdraw_job_input.status and withdraw_job_input.status != original_status:
        existing_withdraw_job.last_transition = datetime.now(timezone.utc)
        
    session.add(existing_withdraw_job)
    session.commit()
    session.refresh(existing_withdraw_job)

    target_assigned_user = (
        withdraw_job_input.assigned_user_id
        if withdraw_job_input.assigned_user_id is not None
        else getattr(existing_withdraw_job, "assigned_user_id", None)
    )

    if original_assigned_user_id != target_assigned_user:
        user_msg = "Reassigned" if original_assigned_user_id else "Assigned"
        if target_assigned_user:
            assigned_to_user = session.get(User, target_assigned_user)
            assigned_name = assigned_to_user.first_name + " " + assigned_to_user.last_name if assigned_to_user else str(target_assigned_user)
            log_audit_event(
                session,
                AuditEventType.JOB_ASSIGNED,
                f"Withdraw Job {id} {user_msg.lower()} to {assigned_name}",
                job_type="withdraw_jobs",
                job_id=id,
            )
        else:
            log_audit_event(
                session,
                AuditEventType.JOB_ASSIGNED,
                f"Withdraw Job {id} unassigned",
                job_type="withdraw_jobs",
                job_id=id,
            )
        session.commit()

    # Log status change if status was updated
    new_status_val = mutated_data.get("status")
    if new_status_val and new_status_val != original_status:
        log_audit_event(
            session,
            AuditEventType.JOB_STATUS_CHANGED,
            f"Status changed from {original_status} to {new_status_val}",
            job_type="withdraw_jobs",
            job_id=id,
        )
        session.commit()

    return existing_withdraw_job


@router.delete("/{job_id}")
def delete_withdraw_job(job_id: int, session: Session = Depends(get_session)):
    """
    Deletes a withdraw job from the database.
    """
    withdraw_job = session.get(WithdrawJob, job_id)
    update_dt = datetime.now(timezone.utc)

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    withdrawal_models = [ItemWithdrawal, NonTrayItemWithdrawal, TrayWithdrawal]
    for model in withdrawal_models:
        session.execute(delete(model).where(model.withdraw_job_id == job_id))

    if withdraw_job.items:
        for item in withdraw_job.items:
            session.execute(update(Item).filter(Item.id == item.id).values(
                update_dt=update_dt,
                withdrawal_dt=None,
                barcode_id=item.withdrawn_barcode_id,
                withdrawn_barcode_id=None,
                withdrawn_location=None,
                withdrawn_internal_location=None,
                withdrawn_loc_bcodes=None,
            ))
    if withdraw_job.non_tray_items:
        for non_tray_item in withdraw_job.non_tray_items:
            session.execute(update(NonTrayItem).filter(
                NonTrayItem.id == non_tray_item.id
            ).values(
                update_dt=update_dt,
                withdrawal_dt=None,
                barcode_id=non_tray_item.withdrawn_barcode_id,
                withdrawn_barcode_id=None,
                withdrawn_location=None,
                withdrawn_internal_location=None,
                withdrawn_loc_bcodes=None,
            ))

    if withdraw_job.trays:
        for tray in withdraw_job.trays:
            for item in tray.items:
                session.execute(update(Item).filter(Item.id == item.id).values(
                    update_dt=update_dt,
                    withdrawal_dt=None,
                    barcode_id=item.withdrawn_barcode_id,
                    withdrawn_barcode_id=None,
                    withdrawn_location=None,
                    withdrawn_internal_location=None,
                    withdrawn_loc_bcodes=None,
                ))

    existing_batch_upload = session.execute(select(BatchUpload).where(
        BatchUpload.withdraw_job_id == job_id)).scalars().first()

    if existing_batch_upload:
        session.execute(update(BatchUpload).where(BatchUpload.withdraw_job_id == job_id).values(withdraw_job_id=None, update_dt=update_dt))

    log_audit_event(
        session,
        AuditEventType.JOB_DELETED,
        f"Withdrawal Job {job_id} deleted",
        job_type="withdraw_jobs",
        job_id=job_id,
    )
    session.delete(withdraw_job)
    session.commit()

    return Response(status_code=204)


@router.post("/{job_id}/add_items", response_model=WithdrawJobDetailOutput)
def add_items_to_withdraw_job(
    job_id: int,
    withdraw_job_input: WithdrawJobInput,
    session: Session = Depends(get_session),
):
    lookup_barcode_value = withdraw_job_input.barcode_value
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_value:
        raise BadRequest(detail="A barcode value must be provided")

    withdraw_job = session.get(WithdrawJob, job_id)
    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    if withdraw_job.status == "Completed":
        raise BadRequest(detail="Withdraw job has already been completed")

    barcode = (
        session.execute(select(Barcode).filter(Barcode.value == lookup_barcode_value))
        .scalars()
        .first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode {lookup_barcode_value} not found")

    item = session.execute(select(Item).filter(Item.barcode_id == barcode.id)).scalars().first()
    non_tray_item = (
        session.execute(select(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id))
        .scalars()
        .first()
    )
    tray = session.execute(select(Tray).filter(Tray.barcode_id == barcode.id)).scalars().first()

    if item:
        tray_id = item.tray_id
        if item.status == "Requested" or item.status == "Withdrawn":
            raise ValidationException(
                detail="Item must be have status if ['In', 'Out']"
            )

        existing_item_withdrawals = (
            session.execute(select(ItemWithdrawal).filter(ItemWithdrawal.item_id == item.id))
            .scalars()
            .all()
        )

        shelf_position = (
            session.execute(select(ShelfPosition)
            .join(Tray)
            .filter(Tray.id == tray_id))
            .scalars()
            .first()
        )

        if validate_item_not_shelved(shelf_position):
            raise ValidationException(detail="Item is not shelved")

        if validate_withdraw_item(
            existing_item_withdrawals, job_id, "Completed", session
        ):
            raise ValidationException(detail="Item is in existing withdraw job")

        session.add(ItemWithdrawal(item_id=item.id, withdraw_job_id=job_id))

        existing_tray_withdrawal = (
            session.execute(select(TrayWithdrawal)
            .filter(TrayWithdrawal.tray_id == tray_id, TrayWithdrawal.withdraw_job_id == job_id))
            .scalars()
            .first()
        )

        if not existing_tray_withdrawal:
            session.add(
                TrayWithdrawal(tray_id=tray_id, withdraw_job_id=withdraw_job.id)
            )

        item.update_dt = update_dt
        session.add(item)

    elif non_tray_item:
        if validate_container_not_shelved(non_tray_item):
            raise ValidationException(detail="Non Tray Item is not shelved")

        if non_tray_item.status == "Requested" or non_tray_item.status == "Withdrawn":
            raise ValidationException(
                detail="Non Tray Item must have status of ['In', 'Out']"
            )

        existing_non_tray_item_withdrawals = (
            session.execute(select(NonTrayItemWithdrawal)
            .filter(NonTrayItemWithdrawal.non_tray_item_id == non_tray_item.id))
            .scalars()
            .all()
        )

        if validate_withdraw_item(
            existing_non_tray_item_withdrawals, job_id, "Completed", session
        ):
            raise ValidationException(
                detail="Non Tray Item is in existing withdraw job"
            )

        session.add(
            NonTrayItemWithdrawal(
                non_tray_item_id=non_tray_item.id, withdraw_job_id=withdraw_job.id
            )
        )

        non_tray_item.update_dt = update_dt
        session.add(non_tray_item)

    elif tray:
        items_for_withdrawal = False

        if not tray.items:
            raise ValidationException(detail="Tray is empty")

        if validate_container_not_shelved(tray):
            raise ValidationException(detail="Tray is not shelved")

        for item in tray.items:
            item_barcode = item.barcode
            if item.status == "Requested" or item.status == "Withdrawn":
                # Note: errored_barcodes logic from previous implementation was missing in this specific block
                # Assuming simple exception raising for single item add
                raise ValidationException(
                    detail=f"Item {item_barcode.value} must have status of ['In', 'Out']"
                )

            existing_withdrawals = (
                session.execute(select(ItemWithdrawal).filter(ItemWithdrawal.item_id == item.id))
                .scalars()
                .all()
            )

            if validate_withdraw_item(
                existing_withdrawals, job_id, "Completed", session
            ):
                raise ValidationException(
                    detail=f"Item {item_barcode.value} is already requested for withdrawal"
                )

            items_for_withdrawal = True
            session.add(
                ItemWithdrawal(item_id=item.id, withdraw_job_id=withdraw_job.id)
            )

            item.update_dt = update_dt
            session.add(item)

        existing_tray_withdrawal = (
            session.execute(select(TrayWithdrawal)
            .filter(
                TrayWithdrawal.tray_id == tray.id,
                TrayWithdrawal.withdraw_job_id == job_id,
            ))
            .scalars()
            .first()
        )

        if not existing_tray_withdrawal and items_for_withdrawal:
            session.add(
                TrayWithdrawal(tray_id=tray.id, withdraw_job_id=withdraw_job.id)
            )

    else:
        raise BadRequest(
            detail=f"No Items or Tray Items with Barcode value {lookup_barcode_value} found"
        )

    session.commit()
    session.refresh(withdraw_job)

    entity_type = "items" if item else ("non_tray_items" if non_tray_item else "trays")
    entity_id = item.id if item else (non_tray_item.id if non_tray_item else tray.id)
    log_audit_event(
        session,
        AuditEventType.ITEM_ADDED,
        f"{lookup_barcode_value} added to Withdrawal Job {job_id}",
        job_type="withdraw_jobs",
        job_id=job_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    session.commit()

    # For return, construct manual dict if relationships aren't loaded, or rely on lazy loading
    return withdraw_job


@router.delete("/{job_id}/remove_items", response_model=WithdrawJobDetailOutput)
def remove_items_from_withdraw_job(
    job_id: int,
    withdraw_job_input: WithdrawJobInput,
    session: Session = Depends(get_session),
) -> WithdrawJobDetailOutput:
    """
    Deletes a tray from a withdraw job in the database.
    """
    lookup_barcode_value = withdraw_job_input.barcode_value
    update_dt = datetime.now(timezone.utc)

    if not lookup_barcode_value:
        raise BadRequest(detail="A barcode value must be provided")

    withdraw_job = session.get(WithdrawJob, job_id)
    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    if withdraw_job.status == "Completed":
        raise BadRequest(detail="Withdraw job has already been completed")

    barcode = (
        session.execute(select(Barcode).filter(Barcode.value == lookup_barcode_value))
        .scalars()
        .first()
    )
    if not barcode:
        raise BadRequest(detail=f"Barcode {lookup_barcode_value} not found")

    item = session.execute(select(Item).filter(Item.barcode_id == barcode.id)).scalars().first()
    non_tray_item = (
        session.execute(select(NonTrayItem).where(NonTrayItem.barcode_id == barcode.id))
        .scalars()
        .first()
    )
    tray = session.execute(select(Tray).filter(Tray.barcode_id == barcode.id)).scalars().first()

    if item:
        request_item = (
            session.execute(select(Request)
            .join(PickList, Request.pick_list_id == PickList.id)
            .filter(
                PickList.id == withdraw_job.pick_list_id, Request.item_id == item.id
            ))
            .scalars()
            .first()
        )

        if request_item:
            session.execute(delete(Request).where(Request.id == request_item.id))

        session.execute(delete(ItemWithdrawal).where(
            ItemWithdrawal.item_id == item.id, ItemWithdrawal.withdraw_job_id == job_id
        ))
        session.execute(update(Item).filter(Item.id == item.id).values(
            status=("In" if item.status in ["Requested", "PickList"] else item.status),
            update_dt=update_dt,
            withdrawal_dt=None,
        ))
    elif non_tray_item:
        request_non_tray_item = (
            session.execute(select(Request)
            .join(PickList, Request.pick_list_id == PickList.id)
            .filter(
                PickList.id == withdraw_job.pick_list_id,
                Request.non_tray_item_id == non_tray_item.id,
            ))
            .scalars()
            .first()
        )

        if request_non_tray_item:
            session.execute(delete(Request).where(Request.id == request_non_tray_item.id))

        session.execute(delete(NonTrayItemWithdrawal).where(
            NonTrayItemWithdrawal.non_tray_item_id == non_tray_item.id, withdraw_job_id == job_id
        ))
        session.execute(update(NonTrayItem).filter(NonTrayItem.id == non_tray_item.id).values(
            status=(
                "In"
                if non_tray_item.status in ["Requested", "PickList"]
                else non_tray_item.status
            ),
            update_dt=update_dt,
            withdrawal_dt=None,
        ))
    elif tray:
        session.execute(delete(TrayWithdrawal).where(
            TrayWithdrawal.tray_id == tray.id, TrayWithdrawal.withdraw_job_id == job_id
        ))
        session.execute(update(Tray).filter(Tray.id == tray.id).values(
            update_dt=update_dt, withdrawal_dt=None
        ))
        for item in tray.items:
            request_item = (
                session.execute(select(Request)
                .join(PickList, Request.pick_list_id == PickList.id)
                .filter(
                    PickList.id == withdraw_job.pick_list_id, Request.item_id == item.id
                ))
                .scalars()
                .first()
            )

            if request_item:
                session.execute(delete(Request).where(Request.id == request_item.id))

            session.execute(delete(ItemWithdrawal).where(
                ItemWithdrawal.item_id == item.id, withdraw_job_id == job_id
            ))
            session.execute(update(Item).filter(Item.id == item.id).values(
                status=(
                    "In"
                    if item.status in ["Requested", "PickList"]
                    else item.status
                ),
                update_dt=update_dt,
                withdrawal_dt=None,
            ))
    else:
        raise BadRequest(
            detail=f"No Items or Tray Items with Barcode value {lookup_barcode_value} found"
        )

    session.commit()
    session.refresh(withdraw_job)

    log_audit_event(
        session,
        AuditEventType.ITEM_REMOVED,
        f"{lookup_barcode_value} removed from Withdrawal Job {job_id}",
        job_type="withdraw_jobs",
        job_id=job_id,
    )
    session.commit()

    return withdraw_job