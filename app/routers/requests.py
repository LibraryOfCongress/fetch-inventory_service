# /code/app/routers/requests.py - REFACRORED TO SQLALCHEMY V2

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session, selectinload # Session and selectinload imported from sqlalchemy.orm now
from sqlalchemy import select, asc, desc, or_, func, update # select/update/func imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.pagination.requests import RequestListPagination
from app.filter_params import SortParams, RequestFilterParams
from app.logger import inventory_logger
from app.models.buildings import Building
from app.models.delivery_locations import DeliveryLocation
from app.models.media_types import MediaType
from app.models.priorities import Priority
from app.models.request_types import RequestType
from app.models.requests import Request, RequestStatus
from app.models.items import Item, ItemStatus
from app.models.non_tray_items import NonTrayItem, NonTrayItemStatus
from app.models.barcodes import Barcode
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.trays import Tray
from app.models.users import User
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
from app.utilities import get_module_shelf_position, check_batch_completion

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.services.audit_service import log_audit_event, AuditEventType

router = APIRouter(
    prefix="/requests",
    tags=["requests"],
    # Router-level gate is authentication only (no global auth exists, so this
    # keeps every route from being public). Reads require can_access_request;
    # writes carry their own create/place/delete permission per endpoint.
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/", response_model=RequestListPagination[RequestListOutput], dependencies=[Depends(RequiresPermission("can_access_request"))])
def get_request_list(
    session: Session = Depends(get_session),
    params: RequestFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get a list of requests
    """
    # Create a query to select all Request from the database with eager loading.
    # Chains are tuned to exactly what RequestListOutput / NestedItemRequestList /
    # NonTrayItemNestedForRequest actually serialize -- avoid loading relationships
    # whose target fields aren't on the list-response schema.
    query = select(Request).where(Request.deleted == False).options(
        # Item-side eager loads
        selectinload(Request.item).selectinload(Item.size_class),
        selectinload(Request.item).selectinload(Item.owner),
        selectinload(Request.item).selectinload(Item.media_type),
        selectinload(Request.item).selectinload(Item.barcode).selectinload(Barcode.type),
        selectinload(Request.item).selectinload(Item.withdrawn_barcode).selectinload(Barcode.type),
        # NestedBarcodeRequestList only exposes type_id (FK column), not the
        # joined `type` relationship, so we stop one level shy here.
        selectinload(Request.item).selectinload(Item.tray).selectinload(Tray.barcode),
        selectinload(Request.item).selectinload(Item.tray).selectinload(Tray.shelf_position).selectinload(ShelfPosition.shelf),
        # NonTrayItem-side eager loads
        selectinload(Request.non_tray_item).selectinload(NonTrayItem.size_class),
        selectinload(Request.non_tray_item).selectinload(NonTrayItem.owner),
        selectinload(Request.non_tray_item).selectinload(NonTrayItem.media_type),
        selectinload(Request.non_tray_item).selectinload(NonTrayItem.barcode).selectinload(Barcode.type),
        selectinload(Request.non_tray_item).selectinload(NonTrayItem.withdrawn_barcode).selectinload(Barcode.type),
        selectinload(Request.non_tray_item).selectinload(NonTrayItem.shelf_position).selectinload(ShelfPosition.shelf),
        # Request-level lookups exposed by RequestListOutput
        selectinload(Request.building),
        selectinload(Request.delivery_location),
        selectinload(Request.request_type),
        selectinload(Request.priority),
        selectinload(Request.pick_list),
        # Note: Request.requested_by is NOT eager-loaded here -- RequestListOutput
        # does not expose it. Detail endpoint still loads it where needed.
    )

    if params.queue:
        # only return unfulfilled requests
        query = query.where(Request.fulfilled == False)
    if params.requestor_name:
        query = query.where(Request.requestor_name.like(f"%{params.requestor_name}%"))
    if params.request_type_id:
        query = query.where(Request.request_type_id.in_(params.request_type_id))
    if params.request_type:
        request_type_subquery = select(RequestType.id).where(
            RequestType.type.in_(params.request_type)
        ).scalar_subquery()
        query = query.where(Request.request_type_id.in_(request_type_subquery))
    if params.requested_by_id:
        query = query.where(Request.requested_by_id.in_(params.requested_by_id))
    if params.requested_by:
        requested_by_subquery = select(User.id).where(
            func.concat(User.first_name, " ", User.last_name).in_(params.requested_by)
        ).scalar_subquery()
        query = query.where(Request.requested_by_id.in_(requested_by_subquery))
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
        ).scalar_subquery()
        query = query.where(Request.building_id.in_(building_subquery))
    if params.unassociated_pick_list:
        query = query.where(Request.pick_list_id == None)
        
    # Barcode Value Logic (V2 Conversion) - Now uses starts-with matching
    if params.barcode_value:
        item_id_subquery = (
            select(Item.id)
            .join(Barcode, Barcode.id == Item.barcode_id)
            .where(Barcode.value.like(f"{params.barcode_value}%"))
            .scalar_subquery()
        )
        non_tray_item_id_subquery = (
            select(NonTrayItem.id)
            .join(Barcode, Barcode.id == NonTrayItem.barcode_id)
            .where(Barcode.value.like(f"{params.barcode_value}%"))
            .scalar_subquery()
        )
        
        query = query.where(
            or_(
                Request.item_id.in_(item_id_subquery),
                Request.non_tray_item_id.in_(non_tray_item_id_subquery),
            )
        )
    if params.item_barcode:
        item_subquery = (
            select(Item.id)
            .join(Barcode, Barcode.id == Item.barcode_id)
            .where(Barcode.value == params.item_barcode)
            .distinct().scalar_subquery()
        )
        query = query.where(Request.item_id.in_(item_subquery))
    if params.non_tray_item_barcode:
        non_tray_item_subquery = (
            select(NonTrayItem.id)
            .join(Barcode, Barcode.id == NonTrayItem.barcode_id)
            .where(Barcode.value == params.non_tray_item_barcode)
            .distinct().scalar_subquery()
        )
        query = query.where(Request.non_tray_item_id.in_(non_tray_item_subquery))
        
    if params.item_status:
        item_subquery = select(Item.id).where(Item.status.in_(params.item_status)).scalar_subquery()
        non_tray_item_subquery = select(NonTrayItem.id).where(
            NonTrayItem.status.in_(params.item_status)
        ).scalar_subquery()

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
            .where(MediaType.name.in_(params.media_type)).scalar_subquery()
        )
        non_tray_item_subquery = (
            select(NonTrayItem.id)
            .join(MediaType, MediaType.id == NonTrayItem.media_type_id)
            .where(MediaType.name.in_(params.media_type)).scalar_subquery()
        )
        query = query.where(
            or_(
                Request.item_id.in_(item_subquery),
                Request.non_tray_item_id.in_(non_tray_item_subquery),
            )
        )
    if params.external_request_id:
        query = query.where(Request.external_request_id.like(f"{params.external_request_id}%"))
    if params.priority_id:
        query = query.where(Request.priority_id.in_(params.priority_id))
    if params.priority:
        priority_subquery = select(Priority.id).where(
            Priority.value.in_(params.priority)
        ).scalar_subquery()
        query = query.where(Request.priority_id.in_(priority_subquery))
    if params.delivery_location:
        delivery_location_subquery = select(DeliveryLocation.id).where(
            DeliveryLocation.name.in_(params.delivery_location)
        ).scalar_subquery()
        query = query.where(
            Request.delivery_location_id.in_(delivery_location_subquery)
        )
    if params.delivery_location_id:
        query = query.where(
            Request.delivery_location_id.in_(params.delivery_location_id)
        )
    if params.item_location:
        # Search both items (in trays) and non-tray items
        # Use ilike for case-insensitive contains matching to handle formatted display values
        # The display shows abbreviated sides (R/L) but database stores full names (Right/Left)
        search_pattern = f"%{params.item_location}%"
        item_location_subquery = (
            select(Item.id)
            .join(Tray, Tray.id == Item.tray_id)
            .join(ShelfPosition, ShelfPosition.id == Tray.shelf_position_id)
            .where(ShelfPosition.location.ilike(search_pattern))
            .distinct().scalar_subquery()
        )
        non_tray_location_subquery = (
            select(NonTrayItem.id)
            .join(ShelfPosition, ShelfPosition.id == NonTrayItem.shelf_position_id)
            .where(ShelfPosition.location.ilike(search_pattern))
            .distinct().scalar_subquery()
        )
        query = query.where(
            or_(
                Request.item_id.in_(item_location_subquery),
                Request.non_tray_item_id.in_(non_tray_location_subquery),
            )
        )
    if params.non_tray_item_location:
        non_tray_item_location_subquery = (
            select(NonTrayItem.id)
            .join(ShelfPosition, ShelfPosition.id == NonTrayItem.shelf_position_id)
            .where(ShelfPosition.location.ilike(f"%{params.non_tray_item_location}%"))
            .distinct().scalar_subquery()
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


@router.get("/{id}", response_model=RequestDetailReadOutput, dependencies=[Depends(RequiresPermission("can_access_request"))])
def get_request_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve request details by ID
    """
    request = session.get(Request, id)
    if request:
        return request

    raise NotFound(detail=f"Request ID {id} Not Found")


@router.post("/", response_model=RequestDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_create_and_submit_manual_requests"))])
def create_request(
    request_input: RequestInput, session: Session = Depends(get_session)
) -> Request:
    """
    Create a Request
    """

    lookup_barcode_value = request_input.barcode_value

    # V2 FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
    barcode = (
        session.execute(select(Barcode).filter(Barcode.value == lookup_barcode_value))
        .scalars()
        .first()
    )

    if not barcode:
        raise BadRequest(detail=f"Barcode value {lookup_barcode_value} not found")

    # V2 FIX
    item = session.execute(select(Item).filter(Item.barcode_id == barcode.id)).scalars().first()
    # V2 FIX
    non_tray_item = (
        session.execute(select(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id))
        .scalars()
        .first()
    )

    if item:
        if item.status == "PickList":
            raise BadRequest(detail="Item is in pick list and cannot be requested")

        existing_request = session.execute(
            select(Request)
            .where(Request.item_id == item.id)
            .where(Request.fulfilled == False)
            .where(Request.deleted == False)
        ).scalars().first()

        if existing_request:
            raise BadRequest(detail="Item is already requested")

        # Verify shelving status directly via the item and its tray
        if (
            not item.tray 
            or not item.tray.scanned_for_shelving 
            or not item.tray.shelf_position_id
            or not item.status == "In"
        ):
            raise BadRequest(detail="Item is not shelved")

        request_input.item_id = item.id
        shelf_position = session.get(ShelfPosition, item.tray.shelf_position_id)

        # V2 UPDATE FIX
        session.execute(
            update(Item).where(Item.id == item.id).values(
                status=ItemStatus.Requested,
                update_dt=datetime.now(timezone.utc),
            )
        )

    elif non_tray_item:
        if non_tray_item.status == "PickList":
            raise BadRequest(
                detail="Non Tray Item Item is in pick list and cannot be " "requested"
            )

        # V2 FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
        existing_non_tray_item = (
            session.execute(select(Request)
            .where(
                Request.non_tray_item_id == non_tray_item.id,
                Request.fulfilled == False,
                Request.deleted == False
            ))
            .scalars()
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

        # V2 UPDATE FIX
        session.execute(
            update(NonTrayItem).where(NonTrayItem.id == non_tray_item.id).values(
                status=NonTrayItemStatus.Requested,
                update_dt=datetime.now(timezone.utc),
            )
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

    # Validate delivery location is allowed for item's owner
    if request_input.delivery_location_id:
        # Get the owner_id from the item or non_tray_item
        owner_id = item.owner_id if item else non_tray_item.owner_id
        
        if owner_id:
            # Import here to avoid circular imports
            from app.models.owner_delivery_locations import OwnerDeliveryLocation
            from app.models.owners import Owner
            
            # Check if owner has any delivery location restrictions
            owner_locations = session.execute(
                select(OwnerDeliveryLocation).where(
                    OwnerDeliveryLocation.owner_id == owner_id
                )
            ).scalars().all()
            
            # If owner has delivery location restrictions, validate
            if owner_locations:
                allowed_location_ids = [ol.delivery_location_id for ol in owner_locations]
                if request_input.delivery_location_id not in allowed_location_ids:
                    # Get owner name for error message
                    owner = session.get(Owner, owner_id)
                    owner_name = owner.name if owner else f"ID {owner_id}"
                    raise BadRequest(
                        detail=f"Delivery location is not allowed for items owned by '{owner_name}'. "
                               f"Please select an allowed delivery location for this owner."
                    )

    new_request = Request(**request_input.model_dump(exclude={"barcode_value"}))

    session.add(new_request)
    session.commit()
    session.refresh(new_request)

    log_audit_event(
        session,
        AuditEventType.REQUEST_CREATED,
        f"Request {new_request.id} created for {lookup_barcode_value}",
        entity_type="items" if item else "non_tray_items",
        entity_id=item.id if item else non_tray_item.id,
    )
    session.commit()

    return new_request


@router.patch("/{id}", response_model=RequestDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_access_request"))])
def update_request(
    id: int, request: RequestUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an existing Request
    """
    try:
        if request.barcode_value:
            lookup_barcode_value = request.barcode_value

            # V2 FIX: session.exec().first() -> session.execute(select(...)).scalars().first()
            item = session.execute(
                select(Item).join(Barcode).where(Barcode.value == lookup_barcode_value)
            ).scalars().first()

            if item:
                request.item_id = item.id
            else:
                # V2 FIX: session.exec().first() -> session.execute(select(...)).scalars().first()
                non_tray_item = session.execute(
                    select(NonTrayItem)
                    .join(Barcode)
                    .where(Barcode.value == lookup_barcode_value)
                ).scalars().first()
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

        log_audit_event(
            session,
            AuditEventType.REQUEST_UPDATED,
            f"Request {id} updated",
            entity_type="items" if existing_request.item_id else "non_tray_items",
            entity_id=existing_request.item_id or existing_request.non_tray_item_id,
        )
        session.commit()

        # Check for batch completion
        if existing_request.status == RequestStatus.Completed and existing_request.batch_upload_id:
            check_batch_completion(session, existing_request.batch_upload_id)

        return existing_request

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", dependencies=[Depends(RequiresPermission("can_delete_request"))])
def delete_request(id: int, session: Session = Depends(get_session)):
    """
    Delete an Request by ID
    """
    request = session.get(Request, id)

    if request:
        # Validate status - cannot delete if PickList or Completed (Active Job)
        if request.status in [RequestStatus.PickList, RequestStatus.Retrieved, RequestStatus.Completed]:
             raise BadRequest(detail=f"Cannot delete request in '{request.status}' status. Only 'New' or 'Failed' requests can be deleted.")

        # Delete request from pick_list_requests
        if request.item:
            item = request.item
            # V2 UPDATE FIX
            session.execute(
                update(Item).where(Item.id == item.id).values(
                    status=ItemStatus.In, update_dt=datetime.now(timezone.utc)
                )
            )

        else:
            #
            non_tray_item = request.non_tray_item

            # V2 UPDATE FIX
            session.execute(
                update(NonTrayItem).where(NonTrayItem.id == non_tray_item.id).values(
                    status=NonTrayItemStatus.In,
                    update_dt=datetime.now(timezone.utc),
                )
            )

        # Deleting request (Soft Delete)
        request.deleted = True
        session.add(request)
        session.commit()

        log_audit_event(
            session,
            AuditEventType.REQUEST_DELETED,
            f"Request {id} deleted",
            entity_type="items" if request.item_id else "non_tray_items",
            entity_id=request.item_id or request.non_tray_item_id,
        )
        session.commit()

        raise HTTPException(
            status_code=204, detail=f"Request ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Request ID {id} Not Found")
