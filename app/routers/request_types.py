from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.request_types import RequestType
from app.schemas.request_types import (
    RequestTypeInput,
    RequestTypeUpdateInput,
    RequestTypeListOutput,
    RequestTypeDetailWriteOutput,
    RequestTypeDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.utilities import get_sorted_query

router = APIRouter(
    prefix="/requests",
    tags=["requests"],
)


@router.get("/types", response_model=Page[RequestTypeListOutput])
def get_request_type_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a list of request types

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - Request Type List Output: The paginated list of request types
    """

    # Create a query to select all Request Type
    query = select(RequestType).distinct()

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(RequestType, query, sort_params)

    return paginate(session, query)


@router.get("/types/{id}", response_model=RequestTypeDetailReadOutput)
def get_request_type_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve request type details by ID
    """
    request_type = session.get(RequestType, id)
    if request_type:
        return request_type

    raise NotFound(detail=f"Request Type ID {id} Not Found")


@router.post("/types", response_model=RequestTypeDetailWriteOutput, status_code=201)
def create_request_type(
    request_type_input: RequestTypeInput, session: Session = Depends(get_session)
) -> RequestType:
    """
    Create a Request Type
    """
    try:
        new_request_type = RequestType(**request_type_input.model_dump())

        # Add the new request type to the database
        session.add(new_request_type)
        session.commit()
        session.refresh(new_request_type)
        return new_request_type

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/types/{id}", response_model=RequestTypeDetailWriteOutput)
def update_request_type(
    id: int, request_type: RequestTypeUpdateInput, session: Session = Depends(get_session)
):
    """
    Update an existing Request Type
    """
    try:
        existing_request_type = session.get(RequestType, id)

        if existing_request_type is None:
            raise NotFound(detail=f"Request Type ID {id} Not Found")

        mutated_data = request_type.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_request_type, key, value)

        setattr(existing_request_type, "update_dt", datetime.utcnow())
        session.add(existing_request_type)
        session.commit()
        session.refresh(existing_request_type)

        return existing_request_type

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/types/{id}")
def delete_request_type(id: int, session: Session = Depends(get_session)):
    """
    Delete an Request Type by ID
    """
    request_type = session.get(RequestType, id)

    if request_type:
        session.delete(request_type)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Request Type ID {id} Deleted "
                                    f"Successfully"
        )

    raise NotFound(detail=f"Request Type ID {id} Not Found")
