from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select
from datetime import datetime, timezone
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams, LadderFilterParams
from app.models.buildings import Building
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.ladders import Ladder
from app.models.ladder_numbers import LadderNumber
from app.schemas.ladders import (
    LadderInput,
    LadderUpdateInput,
    LadderListOutput,
    LadderDetailWriteOutput,
    LadderDetailReadOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)
from app.sorting import BaseSorter, LadderSorter

router = APIRouter(
    prefix="/ladders",
    tags=["ladders"],
)


@router.get("/", response_model=Page[LadderListOutput])
def get_ladder_list(
    session: Session = Depends(get_session),
    params: LadderFilterParams = Depends(),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Ladder Number"),
) -> list:
    """
    Retrieve a paginated list of ladders.

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.
    - search (Optional[str]): The search query.
        - Number: Search for ladders by their number.

    **Returns:**
    - Ladder List Output: A list of ladders.
    """

    # Create a query to retrieve all Ladder
    query = (
        select(Ladder)
        .join(Side, Ladder.side_id == Side.id)
        .join(Aisle, Side.aisle_id == Aisle.id)
        .join(Module, Aisle.module_id == Module.id)
        .join(Building, Module.building_id == Building.id)
    )

    if search:
        query = query.join(
            LadderNumber, Ladder.ladder_number_id == LadderNumber.id
        ).where(LadderNumber.number == search)

    if params.building_id:
        query = query.where(Building.id == params.building_id)
    if params.module_id:
        query = query.where(Module.id == params.module_id)
    if params.aisle_id:
        query = query.where(Aisle.id == params.aisle_id)
    if params.side_id:
        query = query.where(Side.id == params.side_id)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = LadderSorter(Ladder)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=LadderDetailReadOutput)
def get_ladder_detail(
    id: int,
    session: Session = Depends(get_session),
):
    """
    Retrieve the details of a ladder by its ID.

    **Args:**
    - id: The ID of the ladder to retrieve.

    **Returns:**
    - Ladder Detail Read Output: The details of the ladder.

    **Raises:**
    - HTTPException: If the ladder is not found.
    """
    try:
        ladder = session.get(Ladder, id)

        if not ladder:
            raise NotFound(detail=f"Ladder ID {id} Not Found")
        return ladder

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")
    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.post("/", response_model=LadderDetailWriteOutput, status_code=201)
def create_ladder(
    ladder_input: LadderInput, session: Session = Depends(get_session)
) -> Ladder:
    """
    Create a ladder:

    **Args:**
    - Ladder Input: The input data for creating a ladder.

    **Returns:**
    - Ladder Detail Write Output: The created ladder.

    **Raises:**
    - HTTPException: If the ladder already exists.

    **Notes:**
    - **side_id**: Required integer id for related side
    - **ladder_number_id**: Required integer id for related ladder number
    """
    try:
        # Check if ladder # or ladder_number_id
        ladder_number = ladder_input.ladder_number
        ladder_number_id = ladder_input.ladder_number_id
        mutated_data = ladder_input.model_dump(exclude="ladder_number")
        if not ladder_number_id and not ladder_number:
            raise ValidationException(
                detail=f"ladder_number_id OR ladder_number required"
            )
        elif ladder_number and not ladder_number_id:
            # get ladder_number_id from ladder number
            ladder_num_object = (
                session.query(LadderNumber)
                .filter(LadderNumber.number == ladder_number)
                .first()
            )
            if not ladder_num_object:
                raise ValidationException(
                    detail=f"No ladder_number entity exists for ladder number {ladder_number}"
                )
            mutated_data["ladder_number_id"] = ladder_num_object.id

        # new_ladder = Ladder(**ladder_input.model_dump())
        new_ladder = Ladder(**mutated_data)
        session.add(new_ladder)
        session.commit()
        session.refresh(new_ladder)

        return new_ladder

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=LadderDetailWriteOutput)
def update_ladder(
    id: int, ladder: LadderUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a ladder with the given ID.

    **Args:**
    - id: The ID of the ladder to update.
    - Ladder Update Input: The updated ladder data.

    **Returns:**
    - Ladder Detail Write Output: The updated ladder.

    **Raises:**
    - HTTPException: If the ladder with the given ID is not found.
    """

    try:
        existing_ladder = session.get(Ladder, id)

        if not existing_ladder:
            raise NotFound(detail=f"Ladder ID {id} Not Found")

        mutated_data = ladder.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_ladder, key, value)

        setattr(existing_ladder, "update_dt", datetime.now(timezone.utc))

        session.add(existing_ladder)
        session.commit()
        session.refresh(existing_ladder)

        return existing_ladder

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_ladder(id: int, session: Session = Depends(get_session)):
    """
    Delete a ladder with the given ID.

    **Args:**
    - id: The ID of the ladder to delete.

    **Returns:**
    - None

    **Raises:**
    - HTTPException: If the ladder with the given ID is not found.
    """
    ladder = session.get(Ladder, id)

    if ladder:
        session.delete(ladder)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Ladder ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Ladder ID {id} Not Found")
