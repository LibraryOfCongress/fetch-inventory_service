from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime, timezone
from typing import Optional
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy import asc, desc, or_

from app.database.session import get_session
from app.filter_params import SortParams, RequestFilterParams
from app.logger import inventory_logger
from app.models.buildings import Building
from app.models.delivery_locations import DeliveryLocation
from app.models.media_types import MediaType
from app.models.priorities import Priority
from app.models.request_types import RequestType
from app.models.requests import Request
from app.models.items import Item, ItemStatus
from app.models.non_tray_items import NonTrayItem, NonTrayItemStatus
from app.models.barcodes import Barcode
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.trays import Tray
from app.schemas.requests import (
    RequestInput,
    RequestUpdateInput,
    RequestListOutput,
    RequestDetailWriteOutput,
    RequestDetailReadOutput,
)
from app.config.exceptions import (
    BadRequest,
    NotFound,
    InternalServerError,
)
from app.sorting import RequestSorter
from app.utilities import get_module_shelf_position

router = APIRouter(
    prefix="/requests",
    tags=["requests"],
)


@router.get("/", response_model=Page[RequestListOutput])
def get_request_list(
    session: Session = Depends(get_session),
    params: RequestFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get a list of requests

    **Parameters:**
    - building_id: The ID of the build to retrieve requests for.
    - unassociated_pick_list: Whether to retrieve requests with no associated pick list.
    - from_dt: The start date to retrieve requests from.
    - to_dt: The end date to retrieve requests to.
    - requestor_name: The name of the requestor to retrieve requests for.
    - sort_params: The sort parameters to apply to the requests.

    **Returns:**
    - Request List Output: The paginated list of requests.
    """
    # Create a query to select all Request from the database
    query = select(Request)

    if params.queue:
        # only return unfulfilled requests
        query = query.where(Request.fulfilled == False)
    if params.requestor_name:
        query = query.where(Request.requestor_name.like(f"%{params.requestor_name}%"))
    if params.request_type:
        request_type_subquery = select(RequestType.id).where(
            RequestType.type.in_(params.request_type)
        )
        query = query.where(Request.request_type_id.in_(request_type_subquery))
    if params.status:
        query = query.where(Request.status.in_(params.status))
    if params.from_dt:
        query = query.where(Request.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(Request.create_dt <= params.to_dt)
    if params.building_id:
        query = query.where(Request.building_id == params.building_id)
    if params.building_name:
        building_subquery = select(Building.id).where(
            Building.name.in_(params.building_name)
        )
        query = query.where(Request.building_id.in_(building_subquery))
    if params.unassociated_pick_list:
        query = query.where(Request.pick_list_id == None)
    if params.item_barcode:
        item_subquery = (
            select(Item.id)
            .join(Barcode, Barcode.id == Item.barcode_id)
            .where(Barcode.value == params.item_barcode)
            .distinct()
        )
        query = query.where(Request.item_id.in_(item_subquery))
    if params.non_tray_item_barcode:
        non_tray_item_subquery = (
            select(NonTrayItem.id)
            .join(Barcode, Barcode.id == NonTrayItem.barcode_id)
            .where(Barcode.value == params.non_tray_item_barcode)
            .distinct()
        )
        query = query.where(Request.non_tray_item_id.in_(non_tray_item_subquery))
    if params.item_status:
        item_subquery = select(Item.id).where(Item.status.in_(params.item_status))
        non_tray_item_subquery = select(NonTrayItem.id).where(
            NonTrayItem.status.in_(params.item_status)
        )

        query = query.where(
            or_(
                Request.item_id.in_(item_subquery),
                Request.non_tray_item_id.in_(non_tray_item_subquery),
            )
        )
    if params.media_type:
        item_subquery = (
            select(Item.id)
            .join(MediaType, MediaType.id == Item.media_type_id)
            .where(MediaType.name.in_(params.media_type))
        )
        non_tray_item_subquery = (
            select(NonTrayItem.id)
            .join(MediaType, MediaType.id == NonTrayItem.media_type_id)
            .where(MediaType.name.in_(params.media_type))
        )
        query = query.where(
            or_(
                Request.item_id.in_(item_subquery),
                Request.non_tray_item_id.in_(non_tray_item_subquery),
            )
        )
    if params.priority:
        priority_subquery = select(Priority.id).where(
            Priority.value.in_(params.priority)
        )
        query = query.where(Request.priority_id.in_(priority_subquery))
    if params.delivery_location:
        delivery_location_subquery = select(DeliveryLocation.id).where(
            DeliveryLocation.name.in_(params.delivery_location)
        )
        query = query.where(
            Request.delivery_location_id.in_(delivery_location_subquery)
        )
    if params.item_location:
        tem_location_subquery = (
            select(Item.id)
            .join(Tray, Tray.id == Item.tray_id)
            .join(Shelf, Shelf.id == Tray.shelf_id)
            .join(ShelfPosition, ShelfPosition.id == Shelf.shelf_position_id)
            .where(ShelfPosition.location == params.non_tray_item_location)
            .distinct()
        )
        query = query.where(Request.item_id.in_(tem_location_subquery))
    if params.non_tray_item_location:
        non_tray_item_location_subquery = (
            select(NonTrayItem.id)
            .join(ShelfPosition, ShelfPosition.id == NonTrayItem.shelf_position_id)
            .where(ShelfPosition.location == params.non_tray_item_location)
            .distinct()
        )
        query = query.where(
            Request.non_tray_item_id.in_(non_tray_item_location_subquery)
        )

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using RequestSorter
        sorter = RequestSorter(Request)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=RequestDetailReadOutput)
def get_request_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve request details by ID

    **Args:**
    - id: The ID of the request.

    **Returns:**
    - Request Detail Read Output: The details of the request.
    """
    request = session.get(Request, id)
    if request:
        return request

    raise NotFound(detail=f"Request ID {id} Not Found")


@router.post("/", response_model=RequestDetailWriteOutput, status_code=201)
def create_request(
    request_input: RequestInput, session: Session = Depends(get_session)
) -> Request:
    """
    Create a Request

    **Args:**
    - Request Input: The request data.

    **Returns:**
    - Request Detail Write Output: The created request.
    """

    lookup_barcode_value = request_input.barcode_value

    barcode = (
        session.query(Barcode).filter(Barcode.value == lookup_barcode_value).first()
    )

    if not barcode:
        raise BadRequest(detail=f"Barcode value {lookup_barcode_value} not found")

    item = session.query(Item).filter(Item.barcode_id == barcode.id).first()
    non_tray_item = (
        session.query(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id).first()
    )

    if item:
        if item.status == "PickList":
            raise BadRequest(detail="Item is in pick list and cannot be requested")

        existing_request = session.exec(
            select(Request)
            .where(Request.item_id == item.id)
            .where(Request.fulfilled == False)
        ).first()

        if existing_request:
            raise BadRequest(detail="Item is already requested")

        request_input.item_id = item.id
        tray_id = item.tray_id

        shelf_position = session.exec(
            select(ShelfPosition).join(Tray).where(Tray.id == tray_id)
        ).first()

        if (
            not shelf_position.tray.scanned_for_shelving
            or not shelf_position.tray.shelf_position_id
            or not item.status == "In"
        ):
            raise BadRequest(detail="Item is not shelved")

        session.query(Item).filter(Item.id == item.id).update(
            {
                "status": ItemStatus.Requested,
                "update_dt": datetime.now(timezone.utc),
            },
            synchronize_session=False,
        )

    elif non_tray_item:
        if non_tray_item.status == "PickList":
            raise BadRequest(
                detail="Non Tray Item Item is in pick list and cannot be " "requested"
            )

        existing_non_tray_item = (
            session.query(Request)
            .filter(
                Request.non_tray_item_id == non_tray_item.id, Request.fulfilled == False
            )
            .first()
        )

        if existing_non_tray_item:
            raise BadRequest(detail="Non tray item is already requested")

        if (
            not non_tray_item.scanned_for_shelving
            or not non_tray_item.shelf_position_id
            or not non_tray_item.status == "In"
        ):
            raise BadRequest(detail="Non tray item is not shelved")

        session.query(NonTrayItem).filter(NonTrayItem.id == non_tray_item.id).update(
            {
                "status": NonTrayItemStatus.Requested,
                "update_dt": datetime.now(timezone.utc),
            },
            synchronize_session=False,
        )

        request_input.non_tray_item_id = non_tray_item.id
        shelf_position = session.get(ShelfPosition, non_tray_item.shelf_position_id)

    else:
        raise BadRequest(
            detail=f"""Item or Non Tray with barcode value
            {lookup_barcode_value} not found"""
        )

    if not shelf_position:
        raise NotFound(detail=f"Shelf Position Not Found")

    module = get_module_shelf_position(session, shelf_position)

    if module:
        request_input.building_id = module.building_id

    new_request = Request(**request_input.model_dump(exclude={"barcode_value"}))

    # Add the new request to the database
    session.add(new_request)
    session.commit()
    session.refresh(new_request)

    return new_request


@router.patch("/{id}", response_model=RequestDetailWriteOutput)
def update_request(
    id: int, request: RequestUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an existing Request

    **Args:**
    - id: The ID of the Request to update.
    - Request Update Input: The updated Request data.

    **Returns:**
    - Request Detail Write Output: The updated Request.
    """
    try:
        if request.barcode_value:
            lookup_barcode_value = request.barcode_value

            item = session.exec(
                select(Item).join(Barcode).where(Barcode.value == lookup_barcode_value)
            ).first()

            if item:
                request.item_id = item.id
            else:
                non_tray_item = session.exec(
                    select(NonTrayItem)
                    .join(Barcode)
                    .where(Barcode.value == lookup_barcode_value)
                ).first()
                if not non_tray_item:
                    raise NotFound(detail="No items or non_trays found with barcode.")
                request.non_tray_item_id = non_tray_item.id

        existing_request = session.get(Request, id)

        if existing_request is None:
            raise NotFound(detail=f"Request ID {id} Not Found")

        mutated_data = request.model_dump(exclude_unset=True, exclude={"barcode_value"})

        for key, value in mutated_data.items():
            setattr(existing_request, key, value)

        setattr(existing_request, "update_dt", datetime.now(timezone.utc))
        session.add(existing_request)
        session.commit()
        session.refresh(existing_request)

        return existing_request

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_request(id: int, session: Session = Depends(get_session)):
    """
    Delete an Request by ID

    **Args**:
    - id: The ID of the request to delete.

    **Raises**:
    - Not Found: If the request is not found.
    """
    request = session.get(Request, id)

    if request:
        # Delete request from pick_list_requests
        if request.item:
            item = request.item
            session.query(Item).filter(Item.id == item.id).update(
                {"status": ItemStatus.In, "update_dt": datetime.now(timezone.utc)},
                synchronize_session=False,
            )

        else:
            #
            non_tray_item = request.non_tray_item

            session.query(NonTrayItem).filter(
                NonTrayItem.id == non_tray_item.id
            ).update(
                {
                    "status": NonTrayItemStatus.In,
                    "update_dt": datetime.now(timezone.utc),
                },
                synchronize_session=False,
            )

        # Deleting request
        session.delete(request)
        session.commit()

        raise HTTPException(
            status_code=204, detail=f"Request ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Request ID {id} Not Found")
