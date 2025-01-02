from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.subcollection import Subcollection
from app.schemas.subcollection import (
    SubcollectionInput,
    SubcollectionUpdateInput,
    SubcollectionListOutput,
    SubcollectionDetailWriteOutput,
    SubcollectionDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.utilities import get_sorted_query

router = APIRouter(
    prefix="/subcollections",
    tags=["subcollections"],
)


@router.get("/", response_model=Page[SubcollectionListOutput])
def get_subcollection_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Get a paginated list of subcollections

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - Subcollection List Output: The paginated list of subcollections
    """
    # Create a query to select all sides from the database
    query = select(Subcollection).distinct()

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(Subcollection, query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=SubcollectionDetailReadOutput)
def get_subcollection_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of an subcollection from the database using the provided ID
    """
    # Retrieve the subcollection from the database using the provided ID
    subcollection = session.get(Subcollection, id)

    if subcollection:
        return subcollection

    raise NotFound(detail=f"Subcollection ID {id} Not Found")


@router.post("/", response_model=SubcollectionDetailWriteOutput, status_code=201)
def create_subcollection(
    subcollection_input: SubcollectionInput, session: Session = Depends(get_session)
):
    """
    Create a new subcollection
    """
    try:
        # Create a new Subcollection object
        new_subcollection = Subcollection(**subcollection_input.model_dump())
        session.add(new_subcollection)
        session.commit()
        session.refresh(new_subcollection)

        return new_subcollection

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=SubcollectionDetailWriteOutput)
def update_subcollection(
    id: int,
    subcollection: SubcollectionUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Updates an subcollection with the given ID using the provided subcollection data
    """
    try:
        # Get the existing subcollection
        existing_subcollection = session.get(Subcollection, id)

        if not existing_subcollection:
            raise NotFound(detail=f"Subcollection ID {id} Not Found")

        mutated_data = subcollection.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_subcollection, key, value)

        setattr(existing_subcollection, "update_dt", datetime.utcnow())

        session.add(existing_subcollection)
        session.commit()
        session.refresh(existing_subcollection)

        return existing_subcollection

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_subcollection(id: int, session: Session = Depends(get_session)):
    """
    Delete an subcollection with the given id
    """
    subcollection = session.get(Subcollection, id)

    if subcollection:
        session.delete(subcollection)
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Subcollection id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Subcollection ID {id} Not Found")
