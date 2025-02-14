from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime, timezone
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
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
from app.utilities import get_sorted_query

router = APIRouter(
    prefix="/conveyance-bins",
    tags=["conveyance bins"],
)


@router.get("/", response_model=Page[ConveyanceBinListOutput])
def get_conveyance_bin_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of Conveyance Bins from the database.

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - Conveyance Bin List Output: A paginated list of Conveyance Bins.
    """

    # Create a query to retrieve all Conveyance Bin
    query = select(ConveyanceBin).distinct()

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        query = get_sorted_query(ConveyanceBin, query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=ConveyanceBinDetailReadOutput)
def get_conveyance_bin_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve details of a specific conveyance bin by ID.

    **Args:**
    - id: The ID of the conveyance bin to retrieve.

    **Returns:**
    - Conveyance Bin: The details of the requested conveyance bin.
    """

    conveyance_bin = session.get(ConveyanceBin, id)
    if conveyance_bin:
        return conveyance_bin

    raise NotFound(detail=f"Container Type ID {id} Not Found")



@router.post("/", response_model=ConveyanceBinDetailWriteOutput, status_code=201)
def create_conveyance_bin(
    conveyance_bin_input: ConveyanceBinInput, session: Session = Depends(get_session)
):
    """
    Create a new conveyance bin in the database.

    **Parameters:**
    - Conveyance Bin Input: The input data for the new
    conveyance bin.

    **Returns:**
    - Conveyance Bin: The newly created conveyance bin.
    """
    try:
        new_conveyance_bin = ConveyanceBin(**conveyance_bin_input.model_dump())

        session.add(new_conveyance_bin)
        session.commit()
        session.refresh(new_conveyance_bin)

        return new_conveyance_bin

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=ConveyanceBinDetailWriteOutput)
def update_conveyance_bin(
    id: int, conveyance_bin: ConveyanceBinInput, session: Session = Depends(get_session)
):
    """
    Update conveyance bin details by ID.

    **Args:**
    - id: The ID of the conveyance bin to update.
    - ConveyanceBinInput: The new conveyance bin data.

    **Returns:**
    - Conveyance Bin Detail Write Output: The updated conveyance bin details.
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

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_conveyance_bin(id: int, session: Session = Depends(get_session)):
    """
    Delete a conveyance bin by id.

    **Args:**
    - id: The id of the conveyance bin to delete.

    **Raises:**
    - HTTPException: If the conveyance bin with the given id is not found (status
    code 404).
    """
    conveyance_bin = session.get(ConveyanceBin, id)
    if conveyance_bin:
        session.delete(conveyance_bin)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Conveyance Bin ID {id} Deleted "
                                    f"Successfully"
        )

    raise NotFound(detail=f"Conveyance Bin ID {id} Not Found")
