from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy import func, text, asc, desc
from sqlalchemy.orm import aliased
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from starlette.responses import JSONResponse

from app.config.exceptions import (
    NotFound,
    BadRequest,
    ValidationException,
)
from app.database.session import get_session
from app.filter_params import SortParams, JobFilterParams
from app.events import update_shelf_space_after_tray, update_shelf_space_after_non_tray
from app.filter_params import JobFilterParams, SortParams
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
from starlette import status
from app.schemas.withdraw_jobs import (
    WithdrawJobInput,
    WithdrawJobWriteOutput,
    WithdrawJobUpdateInput,
    WithdrawJobListOutput,
    WithdrawJobDetailOutput,
)
from app.utilities import manage_transition, get_module_shelf_position

router = APIRouter(
    prefix="/withdraw-jobs",
    tags=["withdraw jobs"],
)


ShelfBarcodeAlias = aliased(Barcode)
TrayBarcodeAlias = aliased(Barcode)


def validate_withdraw_item(items, job_id, status, session):
    if not items:
        return False

    existing_withdraw_ids = {item.withdraw_job_id for item in items}
    existing_withdraws = (
        session.query(WithdrawJob.id, WithdrawJob.status)
        .filter(WithdrawJob.id.in_(existing_withdraw_ids))
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

    **Parameters:**
    - params: The filter parameters.
        - queue: Filters out completed withdraw jobs.
        - workflow_id: The ID of the workflow.
        - created_by_id: The ID of the user who created the withdraw job list.
        - user_id: The ID of the user.
        - assigned_user: The name of the assigned user.
        - status: The status of the pick list.
        - from_dt: The start date.
        - to_dt: The end date.
    - sort_params: The sort parameters.
        - sort_by: The field to sort by.
        - sort_order: The order to sort by.

    **Returns:**
    - list: A paginated list of withdraw jobs.
    """
    # Create a query to select all Withdraw Job from the database
    query = select(WithdrawJob)

    if params.queue:
        # filter out completed.  maybe someday hide cancelled.
        query = query.where(
            WithdrawJob.status != "Completed"
        )
    if params.status and len(list(filter(None, params.status))) > 0:
        query = query.where(WithdrawJob.status.in_(params.status))
    if params.workflow_id:
        query = query.where(WithdrawJob.id == params.workflow_id)
    if params.user_id:
        query = query.where(WithdrawJob.assigned_user_id.in_(params.user_id))
    if params.assigned_user:
        assigned_user_subquery = (
            select(User.id)
            .where(
                func.concat(User.first_name, ' ', User.last_name).in_(
                    params.assigned_user
                )
            )
            .distinct()
        )
        query = query.where(WithdrawJob.user_id.in_(assigned_user_subquery))
    if params.created_by_id:
        query = query.where(WithdrawJob.created_by_id == params.created_by_id)
    if params.from_dt:
        query = query.where(WithdrawJob.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(WithdrawJob.create_dt <= params.to_dt)


    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using RequestSorter
        sorter = WithdrawJobSorter(WithdrawJob)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=WithdrawJobDetailOutput)
def get_withdraw_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of a withdraw job from the database using the provided ID.

    **Args**:
    - id: The ID of the withdraw job.

    **Returns**:
    - WithdrawJobDetailOutput: The details of the withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job is not found in the database.
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

    **Args**:
    - withdraw_job: The withdraw job data to be created.

    **Returns**:
    - WithdrawJobDetailOutput: The details of the created withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job already exists in the database.
    """
    new_withdraw_job = WithdrawJob(**withdraw_job_input.model_dump())

    session.add(new_withdraw_job)
    session.commit()
    session.refresh(new_withdraw_job)

    return new_withdraw_job


@router.patch("/{id}", response_model=WithdrawJobDetailOutput)
def update_withdraw_job(
    id: int,
    withdraw_job_input: WithdrawJobUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Updates an existing withdraw job in the database.

    **Args**:
    - id: The ID of the withdraw job to be updated.
    - withdraw_job: The updated withdraw job data.

    **Returns**:
    - WithdrawJobDetailOutput: The details of the updated withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job is not found in the database.
    """

    existing_withdraw_job = session.get(WithdrawJob, id)
    updated_dt = datetime.now(timezone.utc)

    if not existing_withdraw_job:
        raise NotFound(detail=f"Withdraw job id {id} not found")

    pick_list = None
    building_id = None
    new_request = []
    audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
    if withdraw_job_input.create_pick_list or withdraw_job_input.add_to_picklist:
        if withdraw_job_input.create_pick_list:
            pick_list = PickList(
                create_dt=updated_dt,
                update_dt=updated_dt,
                withdraw_job_id=id,
            )
            session.add(pick_list)
            session.commit()
            session.refresh(pick_list)
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
                session.query(Request).filter(
                    Request.item == item.id,
                    Request.pick_list_id == None,
                    Request.fulfilled == False,
                ).update(
                    {"pick_list_id": pick_list.id, "update_dt": updated_dt},
                    synchronize_session=False,
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
                session.query(Request).filter(
                    Request.non_tray_item_id == non_tray_item.id,
                    Request.pick_list_id == None,
                    Request.fulfilled == False,
                ).update(
                    {"pick_list_id": pick_list.id, "update_dt": updated_dt},
                    synchronize_session=False,
                )

        if new_request:
            session.bulk_save_objects(new_request)
            start_session_with_audit_info(audit_info, session)
            session.commit()

        session.query(Item).filter(Item.id.in_(item_ids)).update(
            {"status": "PickList", "update_dt": updated_dt},
            synchronize_session=False,
        )
        session.query(NonTrayItem).filter(NonTrayItem.id.in_(non_tray_item_ids)).update(
            {"status": "PickList", "update_dt": updated_dt},
            synchronize_session=False,
        )
        session.query(WithdrawJob).filter(WithdrawJob.id == id).update(
            {"pick_list_id": pick_list.id}
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
            # Step 1: Get the items and their corresponding shelf locations
            items_to_update = session.query(
                Item.id,
                Item.barcode_id,
                ShelfPosition.location,
                ShelfPosition.internal_location,
                ShelfBarcodeAlias.value.label("shelf_barcode_value"),
                TrayBarcodeAlias.value.label("tray_barcode_value"),
            ).join(
                Tray, Item.tray_id == Tray.id
            ).join(
                ShelfPosition, Tray.shelf_position_id == ShelfPosition.id
            ).join(
                Shelf, ShelfPosition.shelf_id == Shelf.id
            ).join(
                ShelfBarcodeAlias, Shelf.barcode_id == ShelfBarcodeAlias.id
            ).join(
                TrayBarcodeAlias, Tray.barcode_id == TrayBarcodeAlias.id
            ).filter(
                Item.id.in_(item_ids)
            ).all()

            # Step 2: Perform the update using a separate query
            for (
                item_id,
                barcode_id,
                location,
                internal_location,
                shelf_barcode_value,
                tray_barcode_value,
            ) in items_to_update:
                session.query(Item).filter(Item.id == item_id).update(
                    {
                        "withdrawal_dt": updated_dt,
                        "withdrawn_barcode_id": barcode_id,
                        "withdrawn_location": location,
                        "withdrawn_internal_location": internal_location,
                        "withdrawn_loc_bcodes":f"{shelf_barcode_value}-{tray_barcode_value}",
                        "barcode_id": None,
                        "update_dt": updated_dt,
                        "status": "Withdrawn",
                        "tray_id": None,
                    },
                    synchronize_session=False,
                )

            # Updating items barcode status to withdrawn
            session.query(Barcode).filter(Barcode.id.in_(item_barcodes)).update(
                {"withdrawn": True, "update_dt": updated_dt},
                synchronize_session=False,
            )
            # Committing the changes
            start_session_with_audit_info(audit_info, session)
            session.commit()

            # leftover deprecated, slated for removal
            # # updating available space for the shelf
            # for item_id in item_ids:
            #     # updating available space for the shelf

            #     shelf = (
            #         session.query(Shelf, Tray)
            #         .join(ShelfPosition, ShelfPosition.shelf_id == Shelf.id)
            #         .join(Item, Item.id == item_id)
            #         .join(Tray, Tray.id == Item.tray_id)
            #         .filter(ShelfPosition.id == Tray.shelf_position_id)
            #         .first()
            #     )

            # Checking if the tray is empty and updating the shelf position
            if tray_ids:

                trays = session.query(Tray).filter(Tray.id.in_(tray_ids))
                empty_trays = [tray for tray in trays if len(tray.items) == 0]

                if empty_trays:
                    tray_barcode_ids = [tray.barcode_id for tray in empty_trays]
                    # Updating Tray barcode status to Withdrawn
                    session.query(Barcode).filter(
                        Barcode.id.in_(tray_barcode_ids)
                    ).update(
                        {"withdrawn": True, "update_dt": updated_dt},
                        synchronize_session=False,
                    )

                    # Step 1: Get the trays and their corresponding shelf locations
                    trays_to_update = session.query(
                        Tray.id,
                        Tray.barcode_id,
                        Tray.shelf_position_id,
                        ShelfPosition.location,
                        ShelfPosition.internal_location,
                        ShelfBarcodeAlias.value.label("shelf_barcode_value"),
                        TrayBarcodeAlias.value.label("tray_barcode_value"),
                    ).join(
                        ShelfPosition, Tray.shelf_position_id == ShelfPosition.id
                    ).join(
                        Shelf, ShelfPosition.shelf_id == Shelf.id
                    ).join(
                        ShelfBarcodeAlias, Shelf.barcode_id == ShelfBarcodeAlias.id
                    ).join(
                        TrayBarcodeAlias, Tray.barcode_id == TrayBarcodeAlias.id
                    ).filter(
                        Tray.id.in_(tray_ids)
                    ).all()

                    # Step 2: Perform the update using a separate query
                    for (
                        tray_id,
                        barcode_id,
                        shelf_position_id,
                        location,
                        internal_location,
                        shelf_barcode_value,
                        tray_barcode_value,
                    ) in trays_to_update:
                        # ignore shelf_position_id. It has to be unpacked and is needed after this update
                        session.query(Tray).filter(Tray.id == tray_id).update(
                            {
                                "shelf_position_id": None,
                                "shelf_position_proposed_id": None,
                                "withdrawn_barcode_id": barcode_id,
                                "withdrawn_location": location,
                                "withdrawn_internal_location": internal_location,
                                "withdrawn_loc_bcodes":f"{shelf_barcode_value}-{tray_barcode_value}",
                                "barcode_id": None,
                                "withdrawal_dt": updated_dt,
                                "update_dt": updated_dt,
                            },
                            synchronize_session=False,
                        )
                    for tray in trays_to_update:
                        # this list still has shelf_position_id in memory
                        update_shelf_space_after_tray(tray, tray.shelf_position_id, None)

        if non_tray_item_ids:
            # Step 1: Fetch necessary data before updating
            non_tray_items_to_update = session.query(
                NonTrayItem.id,
                NonTrayItem.barcode_id,
                NonTrayItem.shelf_position_id,
                ShelfPosition.location,
                ShelfPosition.internal_location,
                ShelfBarcodeAlias.value.label("shelf_barcode_value"),
            ).join(
                ShelfPosition, ShelfPosition.id == NonTrayItem.shelf_position_id
            ).join(
                Shelf, Shelf.id == ShelfPosition.shelf_id
            ).join(
                ShelfBarcodeAlias, ShelfBarcodeAlias.id == Shelf.barcode_id
            ).filter(
                NonTrayItem.id.in_(non_tray_item_ids)
            ).all()

            # Step 2: Perform a separate update for each record
            for (
                item_id,
                barcode_id,
                shelf_position_id,
                location,
                internal_location,
                shelf_barcode_value
            ) in non_tray_items_to_update:
                # ignore shelf_position_id. It has to be unpacked and is needed after this update
                session.query(NonTrayItem).filter(NonTrayItem.id == item_id).update(
                    {
                        "withdrawal_dt": updated_dt,
                        "withdrawn_barcode_id": barcode_id,
                        "withdrawn_location": location,
                        "withdrawn_internal_location": internal_location,
                        "withdrawn_loc_bcodes": f"{shelf_barcode_value}",
                        "barcode_id": None,
                        "update_dt": updated_dt,
                        "status": "Withdrawn",
                        "shelf_position_id": None,
                        "shelf_position_proposed_id": None,
                    },
                    synchronize_session=False,
                )
            session.query(Barcode).filter(
                Barcode.id.in_(non_tray_item_barcodes)
            ).update(
                {"withdrawn": True, "update_dt": updated_dt},
                synchronize_session=False,
            )
            for non_tray_item in non_tray_items_to_update:
                # this list still has shelf_position_id in memory
                update_shelf_space_after_non_tray(non_tray_item, non_tray_item.shelf_position_id, None)

    # Manage transitions and calculate run time if needed
    if withdraw_job_input.status:
        if withdraw_job_input.run_timestamp:
            existing_withdraw_job = manage_transition(
                existing_withdraw_job, withdraw_job_input
            )
        else:
            session.query(WithdrawJob).filter(
                WithdrawJob.id == id
            ).update(
                {
                    "last_transition": updated_dt,
                },
                synchronize_session=False,
            )

    mutated_data = withdraw_job_input.model_dump(
        exclude_unset=True,
        exclude={"run_timestamp", "create_pick_list", "add_to_picklist"},
    )

    for key, value in mutated_data.items():
        setattr(existing_withdraw_job, key, value)

    setattr(existing_withdraw_job, "update_dt", updated_dt)
    start_session_with_audit_info(audit_info, session)
    session.commit()
    session.refresh(existing_withdraw_job)

    return existing_withdraw_job


@router.delete("/{job_id}")
def delete_withdraw_job(job_id: int, session: Session = Depends(get_session)):
    """
    Deletes a withdraw job from the database.

    **Args**:
    - job_id: The ID of the withdraw job.

    **Returns**:
    - None

    **Raises**:
    - HTTPException: If the withdraw job is not found in the database.
    """
    withdraw_job = session.get(WithdrawJob, job_id)
    update_dt = datetime.now(timezone.utc)

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    withdrawal_models = [ItemWithdrawal, NonTrayItemWithdrawal, TrayWithdrawal]
    for model in withdrawal_models:
        session.query(model).filter(model.withdraw_job_id == job_id).delete()

    if withdraw_job.items:
        for item in withdraw_job.items:
            session.query(Item).filter(Item.id == item.id).update(
                {
                    "update_dt": update_dt,
                    "withdrawal_dt": None,
                    "barcode_id": item.withdrawn_barcode_id,
                    "withdrawn_barcode_id": None,
                    "withdrawn_location": None,
                    "withdrawn_internal_location": None,
                    "withdrawn_loc_bcodes": None,
                }
            )
    if withdraw_job.non_tray_items:
        for non_tray_item in withdraw_job.non_tray_items:
            session.query(NonTrayItem).filter(
                NonTrayItem.id == non_tray_item.id
            ).update(
                {
                    "update_dt": update_dt,
                    "withdrawal_dt": None,
                    "barcode_id": non_tray_item.withdrawn_barcode_id,
                    "withdrawn_barcode_id": None,
                    "withdrawn_location": None,
                    "withdrawn_internal_location": None,
                    "withdrawn_loc_bcodes": None,
                }
            )

    if withdraw_job.trays:
        for tray in withdraw_job.trays:
            for item in tray.items:
                session.query(Item).filter(Item.id == item.id).update(
                    {
                        "update_dt": update_dt,
                        "withdrawal_dt": None,
                        "barcode_id": item.withdrawn_barcode_id,
                        "withdrawn_barcode_id": None,
                        "withdrawn_location": None,
                        "withdrawn_internal_location": None,
                        "withdrawn_loc_bcodes": None,
                    }
                )

    existing_batch_upload = session.query(BatchUpload).where(
        BatchUpload.withdraw_job_id == job_id).first()

    if existing_batch_upload:
        session.query(BatchUpload).where(BatchUpload.withdraw_job_id ==
                                         job_id).update({"withdraw_job_id": None,
                                                         "update_dt": update_dt})
    session.delete(withdraw_job)
    session.commit()

    return HTTPException(
        status_code=204,
        detail=f"Withdraw Job id {job_id} Deleted Successfully",
    )


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

    errored_barcodes = []
    withdraw_items = []

    barcode = (
        session.query(Barcode).filter(Barcode.value == lookup_barcode_value).first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode {lookup_barcode_value} not found")

    item = session.query(Item).filter(Item.barcode_id == barcode.id).first()
    non_tray_item = (
        session.query(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id).first()
    )
    tray = session.query(Tray).filter(Tray.barcode_id == barcode.id).first()

    if item:
        tray_id = item.tray_id
        if item.status == "Requested" or item.status == "Withdrawn":
            raise ValidationException(
                detail="Item must be have status if ['In', 'Out']"
            )

        existing_item_withdrawals = (
            session.query(ItemWithdrawal)
            .filter(ItemWithdrawal.item_id == item.id)
            .all()
        )

        shelf_position = (
            session.query(ShelfPosition)
            .join(Tray)
            .filter(Tray.id == tray_id)
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
            session.query(TrayWithdrawal)
            .filter(TrayWithdrawal.tray_id == tray_id, TrayWithdrawal.withdraw_job_id == job_id)
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
            session.query(NonTrayItemWithdrawal)
            .filter(NonTrayItemWithdrawal.non_tray_item_id == non_tray_item.id)
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
                errored_barcodes.append(
                    {
                        "barcode": item_barcode.value,
                        "error": "Item must have status of ['In', 'Out']",
                    }
                )
                continue

            existing_withdrawals = (
                session.query(ItemWithdrawal)
                .filter(ItemWithdrawal.item_id == item.id)
                .all()
            )

            if validate_withdraw_item(
                existing_withdrawals, job_id, "Completed", session
            ):
                errored_barcodes.append(
                    {
                        "barcode": item_barcode.value,
                        "error": "Item is already requested for withdrawal",
                    }
                )
                continue

            existing_item_withdrawals = (
                session.query(ItemWithdrawal)
                .filter(ItemWithdrawal.item_id == item.id)
                .all()
            )

            if validate_withdraw_item(
                existing_item_withdrawals, job_id, "Completed", session
            ):
                errored_barcodes.append(
                    {
                        "barcode": item_barcode.value,
                        "error": "Item is in existing withdraw job",
                    }
                )
                continue

            items_for_withdrawal = True
            withdraw_items.append(
                ItemWithdrawal(item_id=item.id, withdraw_job_id=withdraw_job.id)
            )

            item.update_dt = update_dt
            session.add(item)

        existing_tray_withdrawal = (
            session.query(TrayWithdrawal)
            .filter(
                TrayWithdrawal.tray_id == tray.id,
                TrayWithdrawal.withdraw_job_id == job_id,
            )
            .first()
        )

        if not existing_tray_withdrawal and items_for_withdrawal:
            session.add(
                TrayWithdrawal(tray_id=tray.id, withdraw_job_id=withdraw_job.id)
            )

    else:
        raise BadRequest(
            detail=f"No Items or Tray Items with Barcode value "
            f"{barcode.value} found"
        )

    if withdraw_items:
        session.bulk_save_objects(withdraw_items)

    session.commit()
    session.refresh(withdraw_job)

    if errored_barcodes:
        if not withdraw_items:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"errors": errored_barcodes},
            )
        else:
            withdraw_job_output = WithdrawJobDetailOutput.model_dump(withdraw_job)
            withdraw_job_output["items"] = withdraw_job.items
            withdraw_job_output["trays"] = withdraw_job.trays
            withdraw_job_output["non_tray_items"] = withdraw_job.non_tray_items
            withdraw_job_output["errors"] = errored_barcodes

            return withdraw_job_output

    return withdraw_job


@router.delete("/{job_id}/remove_items", response_model=WithdrawJobDetailOutput)
def remove_items_from_withdraw_job(
    job_id: int,
    withdraw_job_input: WithdrawJobInput,
    session: Session = Depends(get_session),
) -> WithdrawJobDetailOutput:
    """
    Deletes a tray from a withdraw job in the database.

    **Args**:
    - job_id: The ID of the withdraw job.

    **Returns**:
    - Withdraw Job Detail Output: The details of the updated withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job is not found in the database.
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
        session.query(Barcode).filter(Barcode.value == lookup_barcode_value).first()
    )
    if not barcode:
        raise BadRequest(detail=f"Barcode {lookup_barcode_value} not found")

    item = session.query(Item).filter(Item.barcode_id == barcode.id).first()
    non_tray_item = (
        session.query(NonTrayItem).where(NonTrayItem.barcode_id == barcode.id).first()
    )
    tray = session.query(Tray).filter(Tray.barcode_id == barcode.id).first()

    if item:
        # deleting request from pick_list_requests
        request_item = (
            session.query(Request)
            .join(PickList, Request.pick_list_id == PickList.id)
            .filter(
                PickList.id == withdraw_job.pick_list_id, Request.item_id == item.id
            )
            .first()
        )

        if request_item:
            session.query(Request).filter_by(id=request_item.id).delete()

        session.query(ItemWithdrawal).filter_by(
            item_id=item.id, withdraw_job_id=job_id
        ).delete()
        session.query(Item).filter_by(id=item.id).update(
            {
                "status": (
                    "In" if item.status in ["Requested", "PickList"] else item.status
                ),
                "update_dt": update_dt,
                "withdrawal_dt": None,
            }
        )
    elif non_tray_item:
        request_non_tray_item = (
            session.query(Request)
            .join(PickList, Request.pick_list_id == PickList.id)
            .filter(
                PickList.id == withdraw_job.pick_list_id,
                Request.non_tray_item_id == non_tray_item.id,
            )
            .first()
        )

        if request_non_tray_item:
            session.query(Request).filter_by(id=request_non_tray_item.id).delete()

        session.query(NonTrayItemWithdrawal).filter_by(
            non_tray_item_id=non_tray_item.id, withdraw_job_id=job_id
        ).delete()
        session.query(NonTrayItem).filter_by(id=non_tray_item.id).update(
            {
                "status": (
                    "In"
                    if non_tray_item.status in ["Requested", "PickList"]
                    else non_tray_item.status
                ),
                "update_dt": update_dt,
                "withdrawal_dt": None,
            }
        )
    elif tray:
        session.query(TrayWithdrawal).filter_by(
            tray_id=tray.id, withdraw_job_id=job_id
        ).delete()
        session.query(Tray).filter_by(id=tray.id).update(
            {"update_dt": update_dt, "withdrawal_dt": None}
        )
        for item in tray.items:
            # deleting request from pick_list_requests
            request_item = (
                session.query(Request)
                .join(PickList, Request.pick_list_id == PickList.id)
                .filter(
                    PickList.id == withdraw_job.pick_list_id, Request.item_id == item.id
                )
                .first()
            )

            if request_item:
                session.query(Request).filter_by(id=request_item.id).delete()

            session.query(ItemWithdrawal).filter_by(
                item_id=item.id, withdraw_job_id=job_id
            ).delete()
            session.query(Item).filter_by(id=item.id).update(
                {
                    "status": (
                        "In"
                        if item.status in ["Requested", "PickList"]
                        else item.status
                    ),
                    "update_dt": update_dt,
                    "withdrawal_dt": None,
                }
            )
    else:
        raise BadRequest(
            detail=f"No Items or Tray Items with Barcode value {lookup_barcode_value} found"
        )

    session.commit()
    session.refresh(withdraw_job)

    return withdraw_job
