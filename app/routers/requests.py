from app.logger import inventory_logger
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.aisles import Aisle
from app.models.ladders import Ladder
from app.models.modules import Module
from app.models.requests import Request
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.barcodes import Barcode
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.sides import Side
from app.models.trays import Tray
from app.models.pick_list_requests import PickListRequest
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
    ValidationException,
    InternalServerError,
)
from app.utilities import get_module_shelf_position

router = APIRouter(
    prefix="/requests",
    tags=["requests"],
)


@router.get("/", response_model=Page[RequestListOutput])
def get_request_list(
    building_id: int = None,
    unassociated_pick_list: bool = None,
    session: Session = Depends(get_session),
) -> list:
    """
    Get a list of requests

    **Args:**
    - building_id: The ID of the build to retrieve requests for.
    - unassociated_pick_list: Whether to retrieve requests with no associated pick list.

    **Returns:**
    - Request List Output: The paginated list of requests.
    """
    requests = select(Request)

    if building_id is not None:
        requests = requests.where(Request.building_id == building_id)

    if unassociated_pick_list is not None:
        requests = requests.where(
            Request.scanned_for_pick_list == unassociated_pick_list
        )

    return paginate(session, requests)


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

    item = session.exec(
        select(Item).join(Barcode).where(Barcode.value == lookup_barcode_value)
    ).first()

    if item:
        request_input.item_id = item.id
        tray_id = item.tray_id

        shelf_position = session.exec(
            select(ShelfPosition).join(Tray).where(Tray.id == tray_id)
        ).first()

        if (
            not shelf_position.tray.scanned_for_shelving
            or not shelf_position.tray.shelf_position_id
        ):
            raise BadRequest(detail="Item is not shelved")

    else:
        non_tray_item = session.exec(
            select(NonTrayItem)
            .join(Barcode)
            .where(Barcode.value == lookup_barcode_value)
        ).first()

        if not non_tray_item:
            raise NotFound(detail=f"No items or non_trays found with barcode.")

        if (
            not non_tray_item.scanned_for_shelving
            or not non_tray_item.shelf_position_id
        ):
            raise BadRequest(detail="Non tray item is not shelved")

        request_input.non_tray_item_id = non_tray_item.id
        shelf_position = session.get(ShelfPosition, non_tray_item.shelf_position_id)

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
                    raise NotFound(detail=f"No items or non_trays found with barcode.")
                request.non_tray_item_id = non_tray_item.id

        existing_request = session.get(Request, id)

        if existing_request is None:
            raise NotFound(detail=f"Request ID {id} Not Found")

        mutated_data = request.model_dump(exclude_unset=True, exclude={"barcode_value"})

        for key, value in mutated_data.items():
            setattr(existing_request, key, value)

        setattr(existing_request, "update_dt", datetime.utcnow())
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
        pick_list_requests = session.exec(
            select(PickListRequest).where(PickListRequest.request_id == id)
        )

        if pick_list_requests:
            for pick_list_request in pick_list_requests:
                session.delete(pick_list_request)

        # Deleting request
        session.delete(request)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Request ID {id} Deleted " f"Successfully"
        )

    raise NotFound(detail=f"Request ID {id} Not Found")
