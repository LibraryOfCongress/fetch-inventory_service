from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import func

from sqlmodel import Session, select
from datetime import datetime, timezone
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.logger import inventory_logger
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
from app.utilities import get_location, manage_transition

router = APIRouter(
    prefix="/pick-lists",
    tags=["pick lists"],
)


def sort_order_priority(session, pick_list, requests):
    request_data = []
    sorted_requests = set()

    if requests:
        for request in requests:
            if request.item_id:
                item = session.get(Item, request.item_id)
                tray = session.get(Tray, item.tray_id)

                if not tray:
                    continue

                if not tray.shelf_position:
                    continue

                shelf_position = tray.shelf_position

            elif request.non_tray_item_id:
                non_try_item = session.get(NonTrayItem, request.non_tray_item_id)

                if not non_try_item:
                    raise NotFound(
                        detail=f"Non Tray Item ID {request.non_tray_item_id} Not "
                        f"Found"
                    )

                if not non_try_item.shelf_position:
                    continue

                shelf_position = non_try_item.shelf_position

            else:
                raise NotFound(detail="Item Not Found")

            location = get_location(session, shelf_position)

            aisle_priority = (
                location["aisle"].sort_priority or location["aisle_number"].number
            )
            ladder_priority = (
                location["ladder"].sort_priority or location["ladder_number"].number
            )
            shelf_priority = (
                location["shelf"].sort_priority or location["shelf_number"].number
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

            # Append requests not present in sorted_requests due to withdrawn
            # requests (e.g. without shelf location) at the end
            remaining_requests = [req for req in requests if req not in sorted_requests]
            pick_list.requests = unfulfilled_requests + fulfilled_requests + remaining_requests

    return pick_list


@router.get("/", response_model=Page[PickListListOutput])
def get_pick_list_list(
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get a list of pick lists.

    **Parameters:**
    - params: The filter parameters.
        - queue: If true, only return pick lists that are not completed.
        - workflow_id: The ID of the workflow.
        - created_by_id: The ID of the user who created the pick list.
        - building_name: The name of the building.
        - user_id: The ID of the user.
        - assigned_user: The name of the assigned user.
        - status: The status of the pick list.
        - from_dt: The start date.
        - to_dt: The end date.
    - sort_params: The sort parameters.
        - sort_by: The field to sort by.
        - sort_order: The order to sort by.

    **Returns:**
    - Pick List List Output: The paginated list of pick lists.
    """
    # Create a query to select all Pick List from the database
    query = select(PickList)

    try:
        if params.queue:
            query = query.where(PickList.status != "Completed")
        if params.building_name:
            building_subquery = select(Building.id).where(
                Building.name.in_(params.building_name)
            )
            query = query.where(PickList.building_id.in_(building_subquery))
        if params.status and len(list(filter(None, params.status))) > 0:
            query = query.where(PickList.status.in_(params.status))
        if params.workflow_id:
            query = query.where(PickList.id == params.workflow_id)
        if params.user_id:
            query = query.where(PickList.user_id.in_(params.user_id))
        if params.assigned_user:
            assigned_user_subquery = select(User.id).where(
                func.concat(User.first_name, " ", User.last_name).in_(
                    params.assigned_user
                )
            )
            query = query.where(PickList.user_id.in_(assigned_user_subquery))
        if params.created_by_id:
            query = query.where(PickList.created_by_id == params.created_by_id)
        if params.from_dt:
            query = query.where(PickList.create_dt >= params.from_dt)
        if params.to_dt:
            query = query.where(PickList.create_dt <= params.to_dt)

        # Validate and Apply sorting based on sort_params
        if sort_params.sort_by:
            sorter = PickListSorter(PickList)
            query = sorter.apply_sorting(query, sort_params)

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

    return sort_order_priority(session, pick_list, pick_list.requests)


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

    # Updating the items and non-tray items status to Pick List
    item_ids = [request.item_id for request in requests]
    session.query(Item).filter(Item.id.in_(item_ids)).update(
        {"status": ItemStatus.PickList}, synchronize_session=False
    )

    non_tray_item_ids = [request.non_tray_item_id for request in requests]
    session.query(NonTrayItem).filter(NonTrayItem.id.in_(non_tray_item_ids)).update(
        {"status": NonTrayItemStatus.PickList}, synchronize_session=False
    )

    building_id = requests[0].building_id
    new_pick_list = PickList(**pick_list_input.model_dump())
    new_pick_list.building = session.get(Building, building_id)
    # new_pick_list = PickList(building=session.get(Building, building_id))
    session.add(new_pick_list)
    session.flush()

    session.query(Request).filter(Request.id.in_(pick_list_input.request_ids)).update(
        {"pick_list_id": new_pick_list.id, "status": RequestStatus.InProgress},
        synchronize_session=False,
    )

    session.commit()

    if errored_request_ids:
        new_pick_list = new_pick_list.__dict__
        new_pick_list["errored_request_ids"] = errored_request_ids

    return sort_order_priority(session, new_pick_list, new_pick_list.requests)


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
    try:
        existing_pick_list = session.get(PickList, id)

        if not existing_pick_list:
            raise NotFound(detail=f"Pick List ID {id} Not Found")

        if pick_list.status == "Completed":
            session.query()
            request_ids = [
                request.id
                for request in session.query(Request.id)
                .filter(Request.pick_list_id == id)
                .all()
            ]

            if request_ids:
                # Get item ids and update their status
                item_ids = [
                    item.id
                    for item in session.query(Item.id)
                    .join(Request, Item.id == Request.item_id)
                    .filter(Request.id.in_(request_ids))
                    .all()
                ]
                non_tray_item_ids = [
                    non_tray_item.id
                    for non_tray_item in session.query(NonTrayItem.id)
                    .join(Request, NonTrayItem.id == Request.non_tray_item_id)
                    .filter(Request.id.in_(request_ids))
                    .all()
                ]

                if item_ids:
                    session.query(Item).filter(Item.id.in_(item_ids)).update(
                        {
                            "status": ItemStatus.Out,
                            "scanned_for_refile": None,
                            "update_dt": datetime.now(timezone.utc),
                        },
                        synchronize_session=False
                    )

                if non_tray_item_ids:
                    # Get non-tray item ids and update their status
                    session.query(NonTrayItem).filter(
                        NonTrayItem.id.in_(non_tray_item_ids)
                    ).update(
                        {
                            "status": NonTrayItemStatus.Out,
                            "scanned_for_refile": None,
                            "update_dt": datetime.now(timezone.utc),
                        },
                        synchronize_session=False
                    )

                session.query(Request).filter(Request.id.in_(request_ids)).update(
                    {
                        "fulfilled": True,
                        "status": RequestStatus.Completed,
                        "update_dt": datetime.now(timezone.utc),
                    },
                    synchronize_session=False,
                )

                # Handle WithdrawJob and related entities
                existing_withdraw_job = (
                    session.query(WithdrawJob)
                    .filter(WithdrawJob.pick_list_id == id)
                    .first()
                )

                # handle picklist retrieval for Request
                if not existing_withdraw_job:
                    if item_ids:
                        items = session.query(Item).filter(Item.id.in_(item_ids)).all()
                        new_item_retrieval_event = []
                        for item in items:
                            new_item_retrieval_event.append(
                                ItemRetrievalEvent(
                                    item_id=item.id,
                                    owner_id=item.owner_id,
                                    pick_list_id=id,
                                )
                            )
                        session.add_all(new_item_retrieval_event)
                    if non_tray_item_ids:
                        non_tray_items = (
                            session.query(NonTrayItem)
                            .filter(NonTrayItem.id.in_(non_tray_item_ids))
                            .all()
                        )
                        new_non_tray_item_retrieval_event = []
                        for non_tray_items in non_tray_items:
                            new_non_tray_item_retrieval_event.append(
                                NonTrayItemRetrievalEvent(
                                    non_tray_item_id=non_tray_items.id,
                                    owner_id=non_tray_items.owner_id,
                                    pick_list_id=id,
                                )
                            )
                        session.add_all(new_non_tray_item_retrieval_event)

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

        return sort_order_priority(
            session, existing_pick_list, existing_pick_list.requests
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        {
            "pick_list_id": pick_list_id,
            "status": RequestStatus.InProgress,
            "update_dt": datetime.utcnow(),
        },
        synchronize_session=False,
    )

    # Updating the pick list, building_id, run_timestamp, and update_dt
    if not pick_list.building_id:
        pick_list.building_id = existing_requests[0].building_id

    # Updating the items and non-tray items status to Pick List
    item_ids = [request.item_id for request in existing_requests]
    session.query(Item).filter(Item.id.in_(item_ids)).update(
        {"status": "PickList"}, synchronize_session=False
    )

    non_tray_item_ids = [request.non_tray_item_id for request in existing_requests]
    session.query(NonTrayItem).filter(NonTrayItem.id.in_(non_tray_item_ids)).update(
        {"status": "PickList"}, synchronize_session=False
    )

    pick_list.update_dt = update_dt

    session.commit()
    session.refresh(pick_list)

    if errored_request_ids:
        pick_list = pick_list.__dict__
        pick_list["errored_request_ids"] = errored_request_ids

    return sort_order_priority(session, pick_list, pick_list.requests)


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
    update_dt = datetime.now(timezone.utc)

    if not existing_pick_list:
        raise NotFound(
            detail=f"Pick List ID {pick_list_id} or Request ID {request_id} Not Found"
        )

    existing_pick_list.update_dt = update_dt
    # Updating the pick list request
    session.query(Request).filter(Request.id == request_id).update(
        {
            "fulfilled": True,
            "update_dt": update_dt
        }
    )

    # Updating the pick list request Item or Non Tray Item status
    if pick_list_request_input.status:
        request = session.get(Request, request_id)
        if request.item:
            session.query(Item).filter(Item.id == request.item.id).update(
                {
                    "status": pick_list_request_input.status,
                    "update_dt": datetime.now(timezone.utc)
                },
                synchronize_session=False,
            )

        else:
            session.query(NonTrayItem).filter(
                NonTrayItem.id == request.non_tray_item.id
            ).update(
                {
                    "status": pick_list_request_input.status,
                    "update_dt": datetime.now(timezone.utc)
                },
                synchronize_session=False,
            )

    session.commit()
    session.refresh(existing_pick_list)

    return sort_order_priority(session, existing_pick_list, existing_pick_list.requests)


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
    update_dt = datetime.now(timezone.utc)

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
        {
            "pick_list_id": None,
            "status": RequestStatus.New,
            "fulfilled": False,
            "update_dt": update_dt
        },
        synchronize_session=False,
    )

    existing_withdraw_job = session.exec(
        select(WithdrawJob).where(WithdrawJob.pick_list_id == pick_list_id)
    ).first()

    if request.item:
        session.query(Item).filter(Item.id == request.item.id).update(
            {"status": "Requested", "update_dt": update_dt}, synchronize_session=False
        )

        if existing_withdraw_job:
            session.query(ItemWithdrawal).filter(
                ItemWithdrawal.item_id == request.item.id,
                ItemWithdrawal.withdraw_job_id == existing_withdraw_job.id,
            ).delete()

            item_withdrawals = (
                session.query(ItemWithdrawal)
                .filter(ItemWithdrawal.withdraw_job_id == existing_withdraw_job.id)
                .all()
            )

            if not item_withdrawals:
                session.query(TrayWithdrawal).filter(
                    TrayWithdrawal.withdraw_job_id == existing_withdraw_job.id,
                    TrayWithdrawal.tray_id == request.item.tray_id,
                ).delete()

    else:
        session.query(NonTrayItem).filter(
            NonTrayItem.id == request.non_tray_item.id
        ).update(
            {"status": "Requested", "update_dt": update_dt}, synchronize_session=False
        )

        if existing_withdraw_job:
            session.query(NonTrayItemWithdrawal).filter(
                NonTrayItemWithdrawal.non_tray_item_id == request.non_tray_item.id,
                NonTrayItemWithdrawal.withdraw_job_id == existing_withdraw_job.id,
            ).delete()

    # Updating update_dt pick list
    setattr(pick_list, "update_dt", update_dt)

    session.commit()
    session.refresh(pick_list)

    return sort_order_priority(session, pick_list, pick_list.requests)


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

    requests = pick_list.requests

    item_ids = [request.item_id for request in requests]
    non_tray_item_ids = [request.non_tray_item_id for request in requests]

    session.query(Item).filter(Item.id.in_(item_ids)).update(
        {"status": "Requested", "update_dt": datetime.now(timezone.utc)},
        synchronize_session=False,
    )

    session.query(NonTrayItem).filter(NonTrayItem.id.in_(non_tray_item_ids)).update(
        {"status": "Requested", "update_dt": datetime.now(timezone.utc)},
        synchronize_session=False,
    )

    session.query(Request).filter(Request.id.in_([r.id for r in requests])).update(
        {
            "pick_list_id": None,
            "status": RequestStatus.New,
            "fulfilled": False,
            "update_dt": datetime.now(timezone.utc),
        },
        synchronize_session=False,
    )

    session.query(WithdrawJob).filter(WithdrawJob.pick_list_id == id).update(
        {"pick_list_id": None, "update_dt": datetime.now(timezone.utc)},
        synchronize_session=False,
    )

    session.delete(pick_list)
    session.commit()

    raise HTTPException(
        status_code=204, detail=f"Pick list ID {id} Deleted Successfully"
    )
