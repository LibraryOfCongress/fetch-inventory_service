from app.logger import inventory_logger
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record, remove_record
from app.models.aisles import Aisle
from app.models.buildings import Building
from app.models.items import Item
from app.models.ladders import Ladder
from app.models.non_tray_items import NonTrayItem
from app.models.pick_list_requests import PickListRequest
from app.models.pick_lists import PickList
from app.models.requests import Request
from app.models.shelves import Shelf
from app.models.trays import Tray

from app.schemas.requests import RequestDetailReadOutput

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
    ValidationException,
    InternalServerError,
)
from app.utilities import get_location, manage_transition

router = APIRouter(
    prefix="/pick-lists",
    tags=["pick lists"],
)


@router.get("/", response_model=Page[PickListListOutput])
def get_pick_list_list(session: Session = Depends(get_session)) -> list:
    """
    Get a list of pick lists.

    **Returns:**
    - Pick List List Output: The paginated list of pick lists.
    """
    return paginate(session, select(PickList))


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

    for request in requests:
        if request.item_id:
            item = session.get(Item, request.item_id)
            tray = session.get(Tray, item.tray_id)

            if not tray:
                raise NotFound(detail=f"Tray ID {item.tray_id} Not Found")

            if not tray.shelf_position:
                raise NotFound(detail=f"Shelf Position Not Found")

            shelf_position = tray.shelf_position

        elif request.non_tray_item_id:
            non_try_item = session.get(NonTrayItem, request.non_tray_item_id)

            if not non_try_item:
                raise NotFound(
                    detail=f"Non Tray Item ID {request.non_tray_item_id} Not " f"Found"
                )

            if not non_try_item.shelf_position:
                raise NotFound(detail=f"Shelf Position Not Found")

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

        sorted_requests = sorted(
            request_data,
            key=lambda x: (
                x["aisle_priority"],
                x["ladder_priority"],
                x["shelf_priority"],
            ),
        )

        # Extract the sorted request objects
        pick_list.requests = [data["request"] for data in sorted_requests]

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
    requests = (
        session.query(Request).filter(Request.id.in_(pick_list_input.request_ids)).all()
    )

    if not requests:
        raise BadRequest(detail="Request Not Found")

    building_id = requests[0].building_id
    new_pick_list = PickList(building=session.get(Building, building_id))
    session.add(new_pick_list)
    session.flush()

    pick_list_requests = [
        PickListRequest(request_id=request.id, pick_list_id=new_pick_list.id)
        for request in requests
    ]

    session.bulk_save_objects(pick_list_requests)
    session.commit()

    for request in requests:
        request.scanned_for_pick_list = True

    session.commit()

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

    if pick_list.run_timestamp:
        existing_pick_list = manage_transition(existing_pick_list, pick_list)

    mutated_data = pick_list.model_dump(exclude_unset=True, exclude={"run_timestamp"})

    for key, value in mutated_data.items():
        setattr(existing_pick_list, key, value)

    setattr(existing_pick_list, "update_dt", datetime.utcnow())

    return commit_record(session, existing_pick_list)


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
        raise NotFound(detail=f"Some Requests Not Found")

    pick_list_requests = [
        PickListRequest(pick_list_id=pick_list_id, request_id=request.id)
        for request in existing_requests
    ]

    if not pick_list.building_id:
        pick_list.building_id = existing_requests[0].building_id
        commit_record(session, pick_list)

    session.bulk_save_objects(pick_list_requests)
    session.commit()

    session.query(Request).filter(Request.id.in_(pick_list_input.request_ids)).update(
        {"scanned_for_pick_list": True, "update_dt": update_dt}
    )

    # Updating the pick list update_dt time
    pick_list.update_dt = update_dt
    session.commit()
    session.refresh(pick_list)

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

    if pick_list_request_input.run_timestamp:
        existing_pick_list = manage_transition(
            existing_pick_list, pick_list_request_input
        )

    session.commit()

    mutated_data = pick_list_request_input.model_dump(
        exclude_unset=True, exclude={"run_timestamp"}
    )
    mutated_data["update_dt"] = update_dt
    session.query(Request).filter(Request.id == request_id).update(mutated_data)

    # Updating the pick list update_dt time
    existing_pick_list.update_dt = update_dt

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

    # Getting Request, checking if not found, and marking the request as not scanned
    # for pick list
    request = session.query(Request).get(request_id)

    if not request:
        raise NotFound(detail=f"Request ID {request_id} Not Found")

    if not request.scanned_for_pick_list:
        raise BadRequest(detail=f"Request ID {request_id} Not In Pick List")

    # Getting pick list request, checking if not found, and Remove the request from
    # the pick list, and refresh the pick list
    pick_list_request = (
        session.query(PickListRequest)
        .filter_by(pick_list_id=pick_list_id, request_id=request_id)
        .first()
    )

    if not pick_list_request:
        raise NotFound(
            detail=f"Request ID {request_id} Not Found in Pick List ID {pick_list_id}"
        )

    # Marking the pick list request as not scanned for pick list
    request.scanned_for_pick_list = False
    request.scanned_for_retrieval = False
    request.update_dt = update_dt
    commit_record(session, request)

    remove_record(session, pick_list_request)

    # Updating update_dt pick list
    setattr(pick_list, "update_dt", update_dt)

    return commit_record(session, pick_list)


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

    # Delete pick list requests
    if pick_list.requests:
        pick_list_requests = (
            session.query(PickListRequest)
            .filter(PickListRequest.pick_list_id == pick_list.id)
            .all()
        )

        for pick_list_request in pick_list_requests:
            remove_record(session, pick_list_request)

        # Update requests
        requests_to_update = (
            session.query(Request)
            .filter(Request.id.in_([r.request_id for r in pick_list_requests]))
            .all()
        )

        for request in requests_to_update:
            request.scanned_for_pick_list = False
            request.scanned_for_retrieval = False

        session.bulk_update_mappings(Request, requests_to_update)

    session.delete(pick_list)
    session.commit()

    return HTTPException(
        status_code=204, detail=f"Pick list ID {id} Deleted Successfully"
    )
