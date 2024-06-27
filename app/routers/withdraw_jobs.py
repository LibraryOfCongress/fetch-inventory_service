from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.database.session import get_session
from app.models.item_withdrawals import ItemWithdrawal
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.tray_withdrawal import TrayWithdrawal
from app.models.trays import Tray
from app.models.withdraw_jobs import WithdrawJob
from app.models.pick_lists import PickList
from app.schemas.withdraw_jobs import (
    WithdrawJobInput,
    WithdrawJobUpdateInput,
    WithdrawJobListOutput,
    WithdrawJobDetailOutput,
)
from app.utilities import manage_transition

router = APIRouter(
    prefix="/withdraw-jobs",
    tags=["withdraw jobs"],
)


@router.get("/", response_model=Page[WithdrawJobListOutput])
def get_withdraw_job_list(
    queue: bool = Query(default=False), session: Session = Depends(get_session)
) -> list:
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


@router.post("/", response_model=WithdrawJobDetailOutput)
def create_withdraw_job(
    withdraw_job: WithdrawJobInput, session: Session = Depends(get_session)
):
    """
    Creates a new withdraw job in the database.

    **Args**:
    - withdraw_job: The withdraw job data to be created.

    **Returns**:
    - WithdrawJobDetailOutput: The details of the created withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job already exists in the database.
    """
    session.add(withdraw_job)
    session.commit()
    session.refresh(withdraw_job)
    return withdraw_job


@router.patch("/{id}", response_model=WithdrawJobDetailOutput)
def update_withdraw_job(
    id: int,
    withdraw_job: WithdrawJobUpdateInput,
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

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {id} not found")

    if withdraw_job.create_pick_list:
        # create pick list with withdraw job
        new_pick_list = PickList(
            create_dt=datetime.utcnow(),
            update_dt=datetime.utcnow(),
            withdraw_job_id=id,
        )
        session.add(new_pick_list)

        existing_withdraw_job.pick_list_id = new_pick_list.id

        if existing_withdraw_job.items:
            # updating Items status to Withdrawn
            item_ids = []

            for item in existing_withdraw_job.items:
                if item.status == "Out":
                    item_ids.append(item.id)

                if item.status == "Requested":
                    errored_barcodes.append(item.barcode.value)

            session.query(Item).filter(Item.id.in_(item_ids)).update(
                {"status": "Withdrawn"}
            )

        if existing_withdraw_job.non_tray_items:
            # updating non_tray_items status to Withdrawn
            non_tray_item_ids = []

            for non_tray_item in existing_withdraw_job.non_tray_items:
                if non_tray_item.status == "Out":
                    non_tray_item_ids.append(non_tray_item.id)

                if non_tray_item.status == "Requested":
                    errored_barcodes.append(non_tray_item.barcode.value)

            session.query(NonTrayItem).filter(
                NonTrayItem.id.in_(non_tray_item_ids)
            ).update({"status": "Withdrawn"})

        if existing_withdraw_job.trays:
            # updating trays status to Withdrawn
            for tray in existing_withdraw_job.trays:
                exiting_tray = session.get(Tray, tray.id)
                item_ids = []
                for item in tray.items:
                    if item.status == "Out":
                        item_ids.append(item.id)

                    if item.status == "Requested":
                        errored_barcodes.append(item.barcode.value)

                session.query(Item).filter(Item.id.in_(item_ids)).update(
                    {"status": "Withdrawn"}
                )

    mutated_data = withdraw_job.model_dump(
        exclude_unset=True, exclude={"run_timestamp", "create_pick_list"}
    )

    for key, value in mutated_data.items():
        setattr(existing_withdraw_job, key, value)

    if withdraw_job.run_timestamp:
        existing_withdraw_job = manage_transition(existing_withdraw_job, withdraw_job)

    setattr(existing_withdraw_job, "update_dt", datetime.utcnow())

    session.commit()
    session.refresh(withdraw_job)

    if errored_barcodes:
        withdraw_job = withdraw_job.__dict__
        withdraw_job["errored_barcodes"] = errored_barcodes

    return withdraw_job


@router.post("/{job_id}/add_tray/{tray_id}", response_model=WithdrawJobDetailOutput)
def add_tray_to_withdraw_job(
    job_id: int, tray_id: int, session: Session = Depends(get_session)
) -> WithdrawJobDetailOutput:
    """
    Add a tray to a withdraw job in the database.

    **Args**:
    - job_id: The ID of the withdraw job.

    **Returns**:
    - Withdraw Job Detail Output: The details of the updated withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job is not found in the database.
    """
    withdraw_job = session.get(WithdrawJob, job_id)

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    tray_tray_withdrawal = TrayWithdrawal(tray_id=tray_id, withdraw_job_id=job_id)
    session.add(tray_tray_withdrawal)

    session.commit()
    session.refresh(withdraw_job)
    return withdraw_job


@router.delete(
    "/{job_id}/remove_tray/{tray_id}", response_model=WithdrawJobDetailOutput
)
def remove_tray_from_withdraw_job(
    job_id: int, tray_id: int, session: Session = Depends(get_session)
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
    withdraw_job = session.get(WithdrawJob, job_id)

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    session.query(TrayWithdrawal).filter_by(
        tray_id=tray_id, withdraw_job_id=job_id
    ).delete()

    session.commit()
    session.refresh(withdraw_job)
    return withdraw_job


@router.post("/{job_id}/add_item/{item_id}", response_model=WithdrawJobDetailOutput)
def add_item_to_withdraw_job(
    job_id: int, item_id: int, session: Session = Depends(get_session)
) -> WithdrawJobDetailOutput:
    """
    Add an item to a withdraw job in the database.

    **Args**:
    - job_id: The ID of the withdraw job.

    **Returns**:
    - Withdraw Job Detail Output: The details of the updated withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job is not found in the database.
    """
    withdraw_job = session.get(WithdrawJob, job_id)

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    item = session.get(Item, item_id)

    if item.status == "Out":
        raise HTTPException(
            status_code=400, detail=f"Item id {item_id} has a status " f"of Out"
        )

    item_item_withdrawal = ItemWithdrawal(item_id=item_id, withdraw_job_id=job_id)
    session.add(item_item_withdrawal)

    session.commit()
    session.refresh(withdraw_job)

    return withdraw_job


@router.delete(
    "/{job_id}/remove_item/{item_id}", response_model=WithdrawJobDetailOutput
)
def remove_item_from_withdraw_job(
    job_id: int, item_id: int, session: Session = Depends(get_session)
) -> WithdrawJobDetailOutput:
    """
    Deletes an item from a withdraw job in the database.

    **Args**:
    - job_id: The ID of the withdraw job.

    **Returns**:
    - Withdraw Job Detail Output: The details of the updated withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job is not found in the database.
    """
    withdraw_job = session.get(WithdrawJob, job_id)

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    session.query(ItemWithdrawal).filter_by(
        item_id=item_id, withdraw_job_id=job_id
    ).delete()

    session.commit()
    session.refresh(withdraw_job)
    return withdraw_job


@router.post(
    "/{job_id}/add_non_tray/{non_tray_item_id", response_model=WithdrawJobDetailOutput
)
def add_non_tray_item_to_withdraw_job(
    job_id: int, non_tray_item_id: int, session: Session = Depends(get_session)
) -> WithdrawJobDetailOutput:
    """
    Add a non-tray item to a withdraw job in the database.

    **Args**:
    - job_id: The ID of the withdraw job.

    **Returns**:
    - Withdraw Job Detail Output: The details of the updated withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job is not found in the database.
    """
    withdraw_job = session.get(WithdrawJob, job_id)

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    item_non_tray_withdrawal = NonTrayItemWithdrawal(
        non_tray_item_id=non_tray_item_id, withdraw_job_id=job_id
    )
    session.add(item_non_tray_withdrawal)

    session.commit()
    session.refresh(withdraw_job)
    return withdraw_job


@router.delete(
    "/{job_id}/remove_non_tray/{non_tray_item_id}",
    response_model=WithdrawJobDetailOutput,
)
def remove_non_tray_item_from_withdraw_job(
    job_id: int, non_tray_item_id: int, session: Session = Depends(get_session)
) -> WithdrawJobDetailOutput:
    """
    Deletes a non-tray item from a withdraw job in the database.

    **Args**:
    - job_id: The ID of the withdraw job.

    **Returns**:
    - Withdraw Job Detail Output: The details of the updated withdraw job.

    **Raises**:
    - HTTPException: If the withdraw job is not found in the database.
    """
    withdraw_job = session.get(WithdrawJob, job_id)

    if not withdraw_job:
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    session.query(NonTrayItemWithdrawal).filter_by(
        non_tray_item_id=non_tray_item_id, withdraw_job_id=job_id
    ).delete()

    session.commit()
    session.refresh(withdraw_job)
    return withdraw_job
