from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.aisles import Aisle
from app.schemas.aisles import (
    AisleInput,
    AisleListOutput,
    AisleDetailWriteOutput,
    AisleDetailReadOutput,
)

router = APIRouter(
    prefix="/aisles",
    tags=["aisles"],
)


@router.get("/", response_model=Page[AisleListOutput])
def get_aisle_list(session: Session = Depends(get_session)) -> list:
    """
    Get a paginated list of aisles.
    Returns:
        - list[AisleListOutput]: The paginated list of aisles.
    """
    return paginate(session, select(Aisle))


@router.get("/{id}", response_model=AisleDetailReadOutput)
def get_aisle_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of an aisle from the database using the provided ID.
    Args:
        - id (int): The ID of the aisle.
    Returns:
        - AisleDetailReadOutput: The details of the aisle.
    Raises:
        - HTTPException: If the aisle is not found in the database.
    """
    # Retrieve the aisle from the database using the provided ID
    aisle = session.get(Aisle, id)

    if aisle:
        return aisle
    else:
        return HTTPException(status_code=404, detail="Aisle not found")


@router.post("/", response_model=AisleDetailWriteOutput, status_code=201)
def create_aisle(aisle_input: AisleInput, session: Session = Depends(get_session)):
    """
    Create a new aisle.
    Args:
        - aisle_input (AisleInput): The input data for creating a new aisle.
    Returns:
        - AisleDetailWriteOutput: The created aisle.
    Raises:
        - HTTPException: If building_id and module_id are both set.
    Notes:
        - building_id and module_id may not both be set. Only one allowed.
    """
    # Create a new Aisle object
    new_aisle = Aisle(**aisle_input.model_dump())
    session.add(new_aisle)
    session.commit()
    session.refresh(new_aisle)

    return new_aisle


@router.patch("/{id}", response_model=AisleDetailWriteOutput)
def update_aisle(id: int, aisle: AisleInput, session: Session = Depends(get_session)):
    """
    Updates an aisle with the given ID using the provided aisle data.
    Args:
        - id (int): The ID of the aisle to update.
        - aisle (AisleInput): The updated aisle data.
    Returns:
        - AisleDetailWriteOutput: The updated aisle.
    """
    # Get the existing aisle
    try:
        existing_aisle = session.get(Aisle, id)

        if not existing_aisle:
            raise HTTPException(status_code=404)

        mutated_data = aisle.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_aisle, key, value)

        setattr(existing_aisle, "update_dt", datetime.utcnow())

        session.add(existing_aisle)
        session.commit()
        session.refresh(existing_aisle)

        return existing_aisle
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_aisle(id: int, session: Session = Depends(get_session)):
    """
    Delete an aisle with the given id.
    Args:
        - id (int): The id of the aisle to be deleted.
    Returns:
        - HTTPException: If the aisle is not found.
        - None: If the aisle is deleted successfully.
    """
    # Check if the ID is provided and is an integer
    if not id or not isinstance(id, int):
        return HTTPException(status_code=404, detail="Aisle ID is required")

    # Get the aisle
    try:
        aisle = session.get(Aisle, id)

        if aisle:
            session.delete(aisle)
            session.commit()
        else:
            raise HTTPException(status_code=404)
        return HTTPException(status_code=204, detail=f"Aisle {id} deleted successfully")
    except Exception as e:
        return HTTPException(status_code=500, detail=f"{e}")
