from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.config.exceptions import (
    NotFound,
    BadRequest,
)
from app.database.session import get_session, commit_record
from app.logger import inventory_logger
from app.models.barcodes import Barcode
from app.models.item_withdrawals import ItemWithdrawal
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.request_types import RequestType
from app.models.tray_withdrawal import TrayWithdrawal
from app.models.trays import Tray
from app.models.withdraw_jobs import WithdrawJob
from app.models.pick_lists import PickList
from app.models.requests import Request
from app.routers.requests import create_request
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
def get_withdraw_job_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a paginated list of withdraw jobs.

    **Returns:**
    - list: A paginated list of withdraw jobs.
    """
    return paginate(session, select(WithdrawJob))


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
        raise NotFound(detail="Withdraw job id {id} not found")

    return withdraw_job


@router.post("/", response_model=WithdrawJobWriteOutput)
def create_withdraw_job(session: Session = Depends(get_session)):
    """
    Creates a new withdraw job in the database.

    **Args**:
    - withdraw_job: The withdraw job data to be created.

    **Returns**:
    - WithdrawJobDetailOutput: The details of the created withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job already exists in the database.
    """

    return commit_record(session, WithdrawJob())


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
    errored_barcodes = []

    if not existing_withdraw_job:
        raise NotFound(detail=f"Withdraw job id {id} not found")

    pick_list = None
    building_id = None
    new_request = []

    if withdraw_job_input.create_pick_list or withdraw_job_input.add_to_picklist:
        if withdraw_job_input.create_pick_list:
            pick_list = PickList(
                create_dt=datetime.utcnow(),
                update_dt=datetime.utcnow(),
                withdraw_job_id=id,
            )
            session.add(pick_list)
            session.commit()
            session.refresh(pick_list)
        elif withdraw_job_input.add_to_picklist:
            pick_list = session.get(PickList, existing_withdraw_job.pick_list_id)
            if not pick_list:
                raise NotFound(
                    detail=f"Pick list id {withdraw_job_input.pick_list_id} not found"
                )

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
                session.commit()
                session.refresh(pick_list)

            if item.status in ["Requested", "In"]:
                existing_request = (
                    session.query(Request).filter(Request.item_id == item.id).first()
                )
                if existing_request and not existing_request.pick_list_id:
                    session.query(Request).filter(
                        Request.id == existing_request.id
                    ).update(
                        {"pick_list_id": pick_list.id, "update_dt": datetime.utcnow()}
                    )
                elif not existing_request:
                    new_request.append(
                        Request(
                            building_id=building_id,
                            item_id=item.id,
                            pick_list_id=pick_list.id,
                        )
                    )
                if item.status == "In":
                    item_ids.append(item.id)

        for non_tray_item in existing_withdraw_job.non_tray_items:
            if not building_id:
                module = get_module_shelf_position(
                    session, non_tray_item.shelf_position
                )
                building_id = module.building_id
                pick_list.building_id = building_id
                session.add(pick_list)
                session.commit()
                session.refresh(pick_list)

            if non_tray_item.status in ["Requested", "In"]:
                existing_request = (
                    session.query(Request)
                    .filter(Request.non_tray_item_id == non_tray_item.id)
                    .first()
                )
                if existing_request and not existing_request.pick_list_id:
                    session.query(Request).filter(
                        Request.id == existing_request.id
                    ).update(
                        {"pick_list_id": pick_list.id, "update_dt": datetime.utcnow()}
                    )
                elif not existing_request:
                    new_request.append(
                        Request(
                            building_id=building_id,
                            non_tray_item_id=non_tray_item.id,
                            pick_list_id=pick_list.id,
                        )
                    )
                if non_tray_item.status == "In":
                    non_tray_item_ids.append(non_tray_item.id)

        if new_request:
            session.bulk_save_objects(new_request)
            session.query(Item).filter(Item.id.in_(item_ids)).update(
                {"status": "Requested", "update_dt": datetime.utcnow()},
                synchronize_session=False,
            )
            session.query(NonTrayItem).filter(
                NonTrayItem.id.in_(non_tray_item_ids)
            ).update(
                {"status": "Requested", "update_dt": datetime.utcnow()},
                synchronize_session=False,
            )
            session.commit()

        session.query(WithdrawJob).filter(WithdrawJob.id == id).update(
            {"pick_list_id": pick_list.id}
        )

    if withdraw_job_input.status == "Completed":
        item_ids = [item.id for item in existing_withdraw_job.items]
        non_tray_item_ids = [
            non_tray_item.id for non_tray_item in existing_withdraw_job.non_tray_items
        ]
        if item_ids:
            session.query(Item).filter(Item.id.in_(item_ids)).update(
                {"withdrawal_dt": datetime.utcnow(), "status": "Withdrawn"},
                synchronize_session=False,
            )
        if non_tray_item_ids:
            session.query(NonTrayItem).filter(
                NonTrayItem.id.in_(non_tray_item_ids)
            ).update(
                {"withdrawal_dt": datetime.utcnow(), "status": "Withdrawn"},
                synchronize_session=False,
            )

    mutated_data = withdraw_job_input.model_dump(
        exclude_unset=True,
        exclude={"run_timestamp", "create_pick_list", "add_to_picklist"},
    )
    for key, value in mutated_data.items():
        setattr(existing_withdraw_job, key, value)

    if withdraw_job_input.run_timestamp:
        existing_withdraw_job = manage_transition(
            existing_withdraw_job, withdraw_job_input
        )

    setattr(existing_withdraw_job, "update_dt", datetime.utcnow())

    session.commit()
    session.refresh(existing_withdraw_job)

    if errored_barcodes:
        existing_withdraw_job = existing_withdraw_job.__dict__
        existing_withdraw_job["errored_barcodes"] = errored_barcodes

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
    update_dt = datetime.utcnow()

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    withdrawal_models = [ItemWithdrawal, NonTrayItemWithdrawal, TrayWithdrawal]
    for model in withdrawal_models:
        session.query(model).filter(model.withdraw_job_id == job_id).delete()

    if withdraw_job.items:
        for item in withdraw_job.items:
            session.query(Item).filter(Item.id == item.id).update(
                {"update_dt": update_dt}
            )
    if withdraw_job.non_tray_items:
        for non_tray_item in withdraw_job.non_tray_items:
            session.query(NonTrayItem).filter(
                NonTrayItem.id == non_tray_item.id
            ).update({"update_dt": update_dt})

    if withdraw_job.trays:
        for tray in withdraw_job.trays:
            for item in tray.items:
                session.query(Item).filter(Item.id == item.id).update(
                    {"update_dt": update_dt}
                )

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
) -> WithdrawJobDetailOutput:
    lookup_barcode_values = withdraw_job_input.barcode_values
    update_dt = datetime.utcnow()

    if not lookup_barcode_values:
        raise BadRequest(detail="At least one barcode value must be provided")

    withdraw_job = session.get(WithdrawJob, job_id)
    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    errored_barcodes = []
    withdraw_items = []
    withdraw_non_tray_items = []
    withdraw_trays = []

    barcodes = (
        session.query(Barcode).filter(Barcode.value.in_(lookup_barcode_values)).all()
    )

    items = {
        barcode.id: session.query(Item).filter(Item.barcode_id == barcode.id).first()
        for barcode in barcodes
    }
    non_tray_items = {
        barcode.id: session.query(NonTrayItem)
        .filter(NonTrayItem.barcode_id == barcode.id)
        .first()
        for barcode in barcodes
    }
    trays = {
        barcode.id: session.query(Tray).filter(Tray.barcode_id == barcode.id).first()
        for barcode in barcodes
    }

    for barcode in barcodes:
        item = items[barcode.id]
        non_tray_item = non_tray_items[barcode.id]
        tray = trays[barcode.id]

        if item:
            if item.status == "Requested":
                errored_barcodes.append(barcode.value)
                continue
            existing_item_withdrawals = (
                session.query(ItemWithdrawal)
                .filter(ItemWithdrawal.item_id == item.id)
                .all()
            )
            if validate_withdraw_item(
                existing_item_withdrawals, job_id, "Completed", session
            ):
                errored_barcodes.append(barcode.value)
                continue
            withdraw_items.append(
                ItemWithdrawal(item_id=item.id, withdraw_job_id=withdraw_job.id)
            )
            item.update_dt = update_dt
            session.add(item)

        elif non_tray_item:
            if non_tray_item.status == "Requested":
                errored_barcodes.append(barcode.value)
                continue
            existing_non_tray_item_withdrawals = (
                session.query(NonTrayItemWithdrawal)
                .filter(NonTrayItemWithdrawal.non_tray_item_id == non_tray_item.id)
                .all()
            )
            if validate_withdraw_item(
                existing_non_tray_item_withdrawals, job_id, "Completed", session
            ):
                errored_barcodes.append(barcode.value)
                continue
            withdraw_non_tray_items.append(
                NonTrayItemWithdrawal(
                    non_tray_item_id=non_tray_item.id, withdraw_job_id=withdraw_job.id
                )
            )
            non_tray_item.update_dt = update_dt
            session.add(non_tray_item)

        elif tray:
            existing_tray_withdrawal = (
                session.query(TrayWithdrawal)
                .filter(
                    TrayWithdrawal.tray_id == tray.id,
                    TrayWithdrawal.withdraw_job_id == job_id,
                )
                .first()
            )
            if not existing_tray_withdrawal:
                withdraw_trays.append(
                    TrayWithdrawal(tray_id=tray.id, withdraw_job_id=withdraw_job.id)
                )
            for item in tray.items:
                if item.status == "Requested":
                    inventory_logger.filter("HERE 1")
                    errored_barcodes.append(barcode.value)
                    continue
                existing_item_withdrawals = (
                    session.query(ItemWithdrawal)
                    .filter(ItemWithdrawal.item_id == item.id)
                    .all()
                )
                if validate_withdraw_item(
                    existing_item_withdrawals, job_id, "Completed", session
                ):
                    errored_barcodes.append(barcode.value)
                    continue
                withdraw_items.append(
                    ItemWithdrawal(item_id=item.id, withdraw_job_id=withdraw_job.id)
                )
                item.update_dt = update_dt
                session.add(item)

        else:
            errored_barcodes.append(barcode.value)

    session.bulk_save_objects(withdraw_items)
    session.bulk_save_objects(withdraw_non_tray_items)
    session.bulk_save_objects(withdraw_trays)
    session.commit()
    session.refresh(withdraw_job)

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
    lookup_barcode_values = withdraw_job_input.barcode_values
    update_dt = datetime.utcnow()

    errored_barcodes = []

    if not lookup_barcode_values:
        raise BadRequest(detail="At least one barcode value must be provided")

    withdraw_job = session.get(WithdrawJob, job_id)

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    barcodes = (
        session.query(Barcode).filter(Barcode.value.in_(lookup_barcode_values)).all()
    )

    for barcode in barcodes:
        item = session.query(Item).filter(Item.barcode_id == barcode.id).first()
        non_tray_item = (
            session.query(NonTrayItem)
            .where(NonTrayItem.barcode_id == barcode.id)
            .first()
        )
        tray = session.query(Tray).filter(Tray.barcode_id == barcode.id).first()

        if item:
            session.query(ItemWithdrawal).where(
                ItemWithdrawal.item_id == item.id,
                ItemWithdrawal.withdraw_job_id == job_id,
            ).delete()
            session.query(Item).where(Item.id == item.id).update(
                {
                    "update_dt": update_dt,
                }
            )

        elif non_tray_item:
            session.query(NonTrayItemWithdrawal).where(
                NonTrayItemWithdrawal.non_tray_item_id == non_tray_item.id,
                NonTrayItemWithdrawal.withdraw_job_id == job_id,
            ).delete()
            session.query(NonTrayItem).where(NonTrayItem.id == non_tray_item.id).update(
                {
                    "update_dt": update_dt,
                }
            )
        elif tray:
            session.query(TrayWithdrawal).where(
                TrayWithdrawal.tray_id == tray.id,
                TrayWithdrawal.withdraw_job_id == job_id,
            ).delete()

            session.query(Tray).where(Tray.id == tray.id).update(
                {
                    "update_dt": update_dt,
                }
            )

            items = tray.items

            for item in items:
                session.query(ItemWithdrawal).where(
                    ItemWithdrawal.item_id == item.id,
                    ItemWithdrawal.withdraw_job_id == job_id,
                ).delete()
                session.query(Item).where(Item.id == item.id).update(
                    {
                        "update_dt": update_dt,
                    }
                )
        else:
            errored_barcodes.append(barcode.value)
            continue

    session.commit()
    session.refresh(withdraw_job)

    if errored_barcodes:
        withdraw_job = withdraw_job.__dict__
        withdraw_job["errored_barcodes"] = errored_barcodes

    return withdraw_job
