from app.logger import inventory_logger
from fastapi import APIRouter, HTTPException, Depends, Query

from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.filter_params import JobFilterParams
from app.models.buildings import Building
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.item_withdrawals import ItemWithdrawal
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.pick_lists import PickList, PickListStatus
from app.models.requests import Request
from app.models.tray_withdrawal import TrayWithdrawal
from app.models.trays import Tray
from app.models.withdraw_jobs import WithdrawJob
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
from app.utilities import get_location, manage_transition

router = APIRouter(
    prefix="/pick-lists",
    tags=["pick lists"],
)


@router.get("/", response_model=Page[PickListListOutput])
def get_pick_list_list(
    queue: bool = Query(default=False),
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    status: PickListStatus | None = None,
) -> list:
    """
    Get a list of pick lists.

    **Returns:**
    - Pick List List Output: The paginated list of pick lists.
    """
    query = select(PickList).distinct()

    try:
        if queue:
            query = query.where(
                PickList.status != "Completed"
            )
        if params.workflow_id:
            query = query.where(PickList.id == params.workflow_id)
        if params.user_id:
            query = query.where(PickList.user_id == params.user_id)
        if params.created_by_id:
            query = query.where(PickList.created_by_id == params.created_by_id)
        if params.from_dt:
            query = query.where(PickList.create_dt >= params.from_dt)
        if params.to_dt:
            query = query.where(PickList.create_dt <= params.to_dt)
        if status:
            query = query.where(PickList.status == status.value)

        return paginate(session, query)

    except IntegrityError as e:
        raise InternalServerError(detail=f"{e}")


@router.get("/{id}", response_model=PickListDetailOutput)
def get_pick_list_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve pick list details by ID.

    **Args:**
    - id: The ID of the pick list to retrieve.

    **Returns:**
    - Pick List Detail Output: The pick list details.

    **Raises:**
    - HTTPException: If the pick list is not found.
    """
    pick_list = session.get(PickList, id)

    if not pick_list:
        raise NotFound(detail=f"Pick List ID {id} Not Found")

    requests = pick_list.requests
    request_data = []
    sorted_requests = set()

    for request in requests:
        if request.item_id:
            item = session.get(Item, request.item_id)
            tray = session.get(Tray, item.tray_id)

            if not tray:
                raise NotFound(detail=f"Tray ID {item.tray_id} Not Found")

            if not tray.shelf_position:
                continue

        elif request.non_tray_item_id:
            non_try_item = session.get(NonTrayItem, request.non_tray_item_id)

            if not non_try_item:
                raise NotFound(
                    detail=f"Non Tray Item ID {request.non_tray_item_id} Not " f"Found"
                )

            if not non_try_item.shelf_position:
                continue

            shelf_position = non_try_item.shelf_position

        else:
            raise NotFound(detail="Item Not Found")

        location = get_location(session, shelf_position)

        aisle_priority = (
            location["aisle"].sort_priority or location["aisle"].aisle_number_id
        )
        ladder_priority = (
            location["ladder"].sort_priority or location["ladder"].ladder_number_id
        )
        shelf_priority = (
            location["shelf"].sort_priority or location["shelf"].shelf_number_id
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

        # Append requests not present in sorted_requests due to withdrawn
        remaining_requests = [
            req for req in requests if req not in sorted_requests
        ]
        pick_list.requests = sorted_requests + remaining_requests

    return pick_list


@router.post("/", response_model=PickListDetailOutput, status_code=201)
def create_pick_list(
    pick_list_input: PickListInput, session: Session = Depends(get_session)
):
    """
    Create a new pick list.

    **Args:**
    - pick_list: The pick list data to be created.

    **Returns:**
    - Pick List Detail Output: The created pick list details.

    **Raises:**
    - HTTPException: If the pick list already exists.
    """
    errored_request_ids = []
    requests = (
        session.query(Request).filter(Request.id.in_(pick_list_input.request_ids)).all()
    )

    if not requests:
        raise BadRequest(detail="Request Not Found")

    if len(requests) != len(pick_list_input.request_ids):
        errored_request_ids.append(set(requests) - set(pick_list_input.request_ids))

    building_id = requests[0].building_id
    new_pick_list = PickList(**pick_list_input.model_dump())
    new_pick_list.building = session.get(Building, building_id)
    # new_pick_list = PickList(building=session.get(Building, building_id))
    session.add(new_pick_list)
    session.flush()

    session.query(Request).filter(Request.id.in_(pick_list_input.request_ids)).update(
        {"pick_list_id": new_pick_list.id}
    )

    session.commit()

    if errored_request_ids:
        new_pick_list = new_pick_list.__dict__
        new_pick_list["errored_request_ids"] = errored_request_ids

    return new_pick_list


@router.patch("/{id}", response_model=PickListDetailOutput)
def update_pick_list(
    id: int, pick_list: PickListUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an existing pick list.

    **Args:**
    - id: The ID of the pick list to update.
    - pick_list: The updated pick list data.

    **Returns:**
    - Pick List Detail Output: The updated pick list details.

    **Raises:**
    - HTTPException: If the pick list is not found.
    """
    existing_pick_list = session.get(PickList, id)

    if not existing_pick_list:
        raise NotFound(detail=f"Pick List ID {id} Not Found")

    if pick_list.status == "Completed":
        session.query()
        request_ids = [
            request.id
            for request in session.query(Request.id)
            .filter(Request.pick_list_id == id, Request.fulfilled == False)
            .all()
        ]

        if request_ids:
            session.query(Request).filter(Request.id.in_(request_ids)).update(
                {"fulfilled": True}, synchronize_session=False
            )

            # Get item ids and update their status
            item_ids = [
                item.id
                for item in session.query(Item.id)
                .join(Request, Item.id == Request.item_id)
                .filter(Request.id.in_(request_ids))
                .all()
            ]
            session.query(Item).filter(Item.id.in_(item_ids)).update(
                {"status": "Out"}, synchronize_session=False
            )

            # Get non-tray item ids and update their status
            non_tray_item_ids = [
                nt_item.id
                for nt_item in session.query(NonTrayItem.id)
                .join(Request, NonTrayItem.id == Request.non_tray_item_id)
                .filter(Request.id.in_(request_ids))
                .all()
            ]
            session.query(NonTrayItem).filter(
                NonTrayItem.id.in_(non_tray_item_ids)
            ).update({"status": "Out"}, synchronize_session=False)

            # Handle WithdrawJob and related entities
            existing_withdraw_job = (
                session.query(WithdrawJob)
                .filter(WithdrawJob.pick_list_id == id)
                .first()
            )

            if existing_withdraw_job:
                # Get related item ids through the ItemWithdrawal relationship
                withdraw_item_ids = [
                    w.item_id
                    for w in session.query(ItemWithdrawal.item_id)
                    .filter(ItemWithdrawal.withdraw_job_id == existing_withdraw_job.id)
                    .all()
                ]  # Extract IDs from tuples
                session.query(Item).filter(Item.id.in_(withdraw_item_ids)).update(
                    {"status": "Out"}, synchronize_session=False
                )

                # Get related non-tray item ids through the NonTrayItemWithdrawal relationship
                withdraw_non_tray_item_ids = [
                    w.non_tray_item_id
                    for w in session.query(NonTrayItemWithdrawal.non_tray_item_id)
                    .filter(
                        NonTrayItemWithdrawal.withdraw_job_id
                        == existing_withdraw_job.id
                    )
                    .all()
                ]  # Extract IDs from tuples
                session.query(NonTrayItem).filter(
                    NonTrayItem.id.in_(withdraw_non_tray_item_ids)
                ).update({"status": "Out"}, synchronize_session=False)

    if pick_list.status and pick_list.run_timestamp:
        existing_pick_list = manage_transition(existing_pick_list, pick_list)

    mutated_data = pick_list.model_dump(exclude_unset=True, exclude={"run_timestamp"})

    for key, value in mutated_data.items():
        setattr(existing_pick_list, key, value)

    setattr(existing_pick_list, "update_dt", datetime.utcnow())

    session.add(existing_pick_list)
    session.commit()
    session.refresh(existing_pick_list)

    return existing_pick_list


@router.patch("/{pick_list_id}/add_request", response_model=PickListDetailOutput)
def add_request_to_pick_list(
    pick_list_id: int,
    pick_list_input: PickListInput,
    session: Session = Depends(get_session),
):
    """
    Add a request to an existing pick list.

    **Args:**
    - pick_list_id: The ID of the pick list to add the request to.
    - request_ids: The IDs of the requests to add to the pick list.

    **Returns:**
    - Pick List Detail Output: The updated pick list details.

    **Raises:**
    - HTTPException: If the pick list or request is not found.
    """
    if not pick_list_id:
        raise BadRequest(detail="Pick List ID Not Found")

    pick_list = session.get(PickList, pick_list_id)
    update_dt = datetime.utcnow()
    errored_request_ids = []

    if pick_list.status == "Completed":
        raise BadRequest(detail="Pick List Already Completed")

    if not pick_list:
        raise NotFound(detail=f"Pick List ID {pick_list_id} Not Found")

    if not pick_list_input.request_ids:
        raise BadRequest(detail="Request IDs Not Found")

    # Getting Request, checking if not found, and marking the request as scanned for
    # pick list
    existing_requests = session.exec(
        select(Request).where(Request.id.in_(pick_list_input.request_ids))
    ).all()

    if len(existing_requests) != len(pick_list_input.request_ids):
        errored_request_ids.append(
            set(existing_requests) - set(pick_list_input.request_ids)
        )

    session.query(Request).filter(Request.id.in_(pick_list_input.request_ids)).update(
        {"pick_list_id": pick_list_id, "update_dt": datetime.utcnow()},
        synchronize_session="fetch",
    )

    # Updating the pick list, building_id, run_timestamp, and update_dt
    if not pick_list.building_id:
        pick_list.building_id = existing_requests[0].building_id

    pick_list.update_dt = update_dt

    session.commit()
    session.refresh(pick_list)

    if errored_request_ids:
        pick_list = pick_list.__dict__
        pick_list["errored_request_ids"] = errored_request_ids

    return pick_list


@router.patch(
    "/{pick_list_id}/update_request/{request_id}", response_model=PickListDetailOutput
)
def update_request_for_pick_list(
    pick_list_id: int,
    request_id: int,
    pick_list_request_input: PickListUpdateRequestInput,
    session: Session = Depends(get_session),
):
    """
    Update a request for an existing pick list.

    **Args:**
    - pick_list_id: The ID of the pick list to update the request for.
    - request_id: The ID of the request to update.
    - pick_list_request_input: The updated request data.

    **Returns:**
    - Pick List Detail Output: The updated pick list details.

    **Raises:**
    - HTTPException: If the pick list or request is not found.
    """
    existing_pick_list = (
        session.query(PickList)
        .filter(PickList.id == pick_list_id)
        .filter(PickList.requests.any(Request.id == request_id))
        .first()
    )
    update_dt = datetime.utcnow()

    if not existing_pick_list:
        raise NotFound(
            detail=f"Pick List ID {pick_list_id} or Request ID {request_id} Not Found"
        )

    mutated_data = pick_list_request_input.model_dump(
        exclude_unset=True, exclude={"run_timestamp", "status"}
    )
    mutated_data["update_dt"] = update_dt
    existing_pick_list.update_dt = update_dt

    # Updating the pick list request
    session.query(Request).filter(Request.id == request_id).update(mutated_data)

    # Updating the pick list request Item or Non Tray Item status
    if pick_list_request_input.status:
        request = session.get(Request, request_id)
        if request.item:
            session.query(Item).filter(Item.id == request.item.id).update(
                {"status": pick_list_request_input.status},
                synchronize_session="fetch",
            )

        else:
            session.query(NonTrayItem).filter(
                NonTrayItem.id == request.non_tray_item.id
            ).update(
                {"status": pick_list_request_input.status},
                synchronize_session="fetch",
            )

    session.commit()
    session.refresh(existing_pick_list)

    return existing_pick_list


@router.delete(
    "/{pick_list_id}/remove_request/{request_id}", response_model=PickListDetailOutput
)
def remove_request_from_pick_list(
    pick_list_id: int, request_id: int, session: Session = Depends(get_session)
):
    """
    Remove a request from an existing pick list.

    **Args:**
    - pick_list_id: The ID of the pick list to remove the request from.
    - request_id: The ID of the request to remove from the pick list.

    **Returns:**
    - Pick List Detail Output: The updated pick list details.

    **Raises:**
    - HTTPException: If the pick list or request is not found.
    - HTTPException: If the request is not found in the pick list.
    """
    pick_list = session.query(PickList).get(pick_list_id)
    update_dt = datetime.utcnow()

    if not pick_list:
        raise NotFound(detail=f"Pick List ID {pick_list_id} Not Found")

    if pick_list.status == "Completed":
        raise BadRequest(detail="Pick List Already Completed")

    # Getting Request, checking if not found, and marking the request as not scanned
    # for pick list
    request = session.query(Request).get(request_id)

    if not request:
        raise NotFound(detail=f"Request ID {request_id} Not Found")

    session.query(Request).filter(Request.id == request_id).update(
        {"update_dt": datetime.utcnow(), "pick_list_id": None},
        synchronize_session="fetch",
    )

    # Updating update_dt pick list
    setattr(pick_list, "update_dt", update_dt)

    session.commit()
    session.refresh(pick_list)

    return pick_list


@router.delete("/{id}")
def delete_pick_list(id: int, session: Session = Depends(get_session)):
    """
    Delete an existing pick list.

    **Args:**
    - id: The ID of the pick list to delete.

    **Returns:**
    - None: If the pick list is deleted successfully.

    **Raises:**
    - HTTPException: If the pick list is not found.
    """
    pick_list = session.get(PickList, id)

    if not pick_list:
        raise NotFound(detail=f"Pick List ID {id} Not Found")

    session.query(Request).filter(
        Request.id.in_([r.id for r in pick_list.requests])
    ).update(
        {"pick_list_id": None, "update_dt": datetime.utcnow()},
        synchronize_session="fetch",
    )

    session.delete(pick_list)
    session.commit()

    raise HTTPException(
        status_code=204, detail=f"Pick list ID {id} Deleted Successfully"
    )
