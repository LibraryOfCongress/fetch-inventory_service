# /code/app/routers/conveyance_bins.py - REFACRORED TO SQLALCHEMY V2

from fastapi.responses import Response
from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.conveyance_bins import ConveyanceBin

from app.schemas.conveyance_bins import (
    ConveyanceBinInput,
    ConveyanceBinListOutput,
    ConveyanceBinDetailWriteOutput,
    ConveyanceBinDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/conveyance-bins",
    tags=["conveyance bins"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/", response_model=Page[ConveyanceBinListOutput])
def get_conveyance_bin_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of Conveyance Bins from the database.
    """

    # Create a query to retrieve all Conveyance Bin
    query = select(ConveyanceBin)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using RequestSorter
        sorter = BaseSorter(ConveyanceBin)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=ConveyanceBinDetailReadOutput)
def get_conveyance_bin_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve details of a specific conveyance bin by ID.
    """

    conveyance_bin = session.get(ConveyanceBin, id)
    if conveyance_bin:
        return conveyance_bin

    raise NotFound(detail=f"Container Type ID {id} Not Found")


@router.post("/", response_model=ConveyanceBinDetailWriteOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def create_conveyance_bin(
    conveyance_bin_input: ConveyanceBinInput, session: Session = Depends(get_session)
):
    """
    Create a new conveyance bin in the database.
    """
    try:
        new_conveyance_bin = ConveyanceBin(**conveyance_bin_input.model_dump())

        session.add(new_conveyance_bin)
        session.commit()
        session.refresh(new_conveyance_bin)

        return new_conveyance_bin

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=ConveyanceBinDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def update_conveyance_bin(
    id: int, conveyance_bin: ConveyanceBinInput, session: Session = Depends(get_session)
):
    """
    Update conveyance bin details by ID.
    """
    try:
        existing_conveyance_bin = session.get(ConveyanceBin, id)

        if not existing_conveyance_bin:
            raise NotFound(detail=f"Conveyance Bin ID {id} Not Found")

        mutated_data = conveyance_bin.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_conveyance_bin, key, value)

        setattr(existing_conveyance_bin, "update_dt", datetime.now(timezone.utc))

        session.add(existing_conveyance_bin)
        session.commit()
        session.refresh(existing_conveyance_bin)

        return existing_conveyance_bin

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", status_code=204, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def delete_conveyance_bin(id: int, session: Session = Depends(get_session)):
    """
    Delete a conveyance bin by id.
    """
    conveyance_bin = session.get(ConveyanceBin, id)
    if conveyance_bin:
        session.delete(conveyance_bin)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Conveyance Bin ID {id} Not Found")
