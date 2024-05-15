from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.requests import Request
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.barcodes import Barcode
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


router = APIRouter(
    prefix="/requests",
    tags=["requests"],
)


@router.get("/", response_model=Page[RequestListOutput])
def get_request_list(session: Session = Depends(get_session)) -> list:
    """
    Get a list of requests
    """
    return paginate(session, select(Request))


@router.get("/{id}", response_model=RequestDetailReadOutput)
def get_request_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve request details by ID
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
    """
    try:
        lookup_barcode_value = request_input.barcode_value

        item = session.exec(
            select(Item).join(Barcode).where(Barcode.value == lookup_barcode_value)
        ).first()

        if item:
            request_input.item_id = item.id
        else:
            non_tray_item = session.exec(
                select(NonTrayItem).join(Barcode).where(
                    Barcode.value == lookup_barcode_value
                )
            ).first()
            if not non_tray_item:
                raise NotFound(detail=f"No items or non_trays found with barcode.")
            request_input.non_tray_item_id = non_tray_item.id

        new_request = Request(**request_input.model_dump(
            exclude={'barcode_value'}
        ))

        # Add the new request to the database
        session.add(new_request)
        session.commit()
        session.refresh(new_request)
        return new_request

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=RequestDetailWriteOutput)
def update_request(
    id: int, request: RequestUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an existing Request
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
                    select(NonTrayItem).join(Barcode).where(
                        Barcode.value == lookup_barcode_value
                    )
                ).first()
                if not non_tray_item:
                    raise NotFound(detail=f"No items or non_trays found with barcode.")
                request.non_tray_item_id = non_tray_item.id

        existing_request = session.get(Request, id)

        if existing_request is None:
            raise NotFound(detail=f"Request ID {id} Not Found")

        mutated_data = request.model_dump(
            exclude_unset=True,
            exclude={'barcode_value'}
        )

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
    """
    request = session.get(Request, id)

    if request:
        session.delete(request)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Request ID {id} Deleted "
                                    f"Successfully"
        )

    raise NotFound(detail=f"Request ID {id} Not Found")
