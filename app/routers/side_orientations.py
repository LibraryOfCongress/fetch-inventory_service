# /code/app/routers/side_orientations.py - REFACRORED TO SQLALCHEMY V2

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
from typing import Optional

from app.database.session import get_session
from app.filter_params import SortParams
from app.models.side_orientations import SideOrientation

from app.schemas.side_orientations import (
    SideOrientationInput,
    SideOrientationListOutput,
    SideOrientationDetailWriteOutput,
    SideOrientationDetailReadOutput,
    SideOrientationUpdateInput
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/sides",
    tags=["sides"],
    # Authenticated-only at the router level; writes carry the manage permission
    # per-endpoint so GETs aren't gated by admin perms.
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/orientations", response_model=Page[SideOrientationListOutput])
def get_side_orientation_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of side orientations.
    """
    # Create a query to select all Side Orientation
    query = select(SideOrientation)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(SideOrientation)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/orientations/{id}", response_model=SideOrientationDetailReadOutput)
def get_side_orientation_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a side orientation by its ID.
    """

    side_orientation = session.get(SideOrientation, id)

    if side_orientation:
        return side_orientation

    raise NotFound(detail=f"Side Orientation ID {id} Not Found")


@router.post(
    "/orientations", response_model=SideOrientationDetailWriteOutput, status_code=201,
    dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))]
)
def create_side_orientation(
    side_orientation_input: SideOrientationInput,
    session: Session = Depends(get_session),
):
    """
    Create a new side orientation record.
    """
    try:
        # Create a new side orientation
        new_side_orientation = SideOrientation(**side_orientation_input.model_dump())
        session.add(new_side_orientation)
        session.commit()
        session.refresh(new_side_orientation)

        return new_side_orientation

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")

@router.patch("/orientations/{id}", response_model=SideOrientationDetailWriteOutput, dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def update_side_orientation(
    id: int,
    side_orientation: SideOrientationUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a side orientation by its ID.
    """
    try:
        existing_side_orientation = session.get(SideOrientation, id)

        if not existing_side_orientation:
            raise NotFound(detail=f"Side Orientation ID {id} Not Found")

        mutated_data = side_orientation.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_side_orientation, key, value)

        setattr(existing_side_orientation, "update_dt", datetime.now(timezone.utc))

        session.add(existing_side_orientation)
        session.commit()
        session.refresh(existing_side_orientation)

        return existing_side_orientation

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/orientations/{id}", dependencies=[Depends(RequiresPermission("can_manage_list_configurations"))])
def delete_side_orientation(id: int, session: Session = Depends(get_session)):
    """
    Deletes a side orientation with the given ID.
    """
    side_orientation = session.get(SideOrientation, id)

    if side_orientation:
        session.delete(side_orientation)
        session.commit()

        return Response(status_code=204)

    raise NotFound(detail=f"Side Orientation ID {id} Not Found")
