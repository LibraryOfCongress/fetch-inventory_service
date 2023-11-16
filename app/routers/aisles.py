from typing import Sequence

from fastapi import APIRouter, HTTPException, Depends, Response
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


@router.get("/", response_model=list[AisleListOutput])
def get_aisle_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a list of aisles.
    """
    # Create a query to select all records from the Aisle table
    query = select(Aisle)

    # Execute the query using the session and return all the results
    try:
        results = session.exec(query)
        return results.all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.get("/{id}", response_model=AisleDetailReadOutput)
def get_aisle_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of an aisle.
    """

    # Check if the ID is provided and is an integer
    if not id or not isinstance(id, int):
        return HTTPException(status_code=404, detail="Aisle ID is required")

    try:
        # Retrieve the aisle from the database using the provided ID
        aisle = session.get(Aisle, id)

        if aisle:
            return aisle
        else:
            return HTTPException(status_code=404, detail="Aisle not found")

    except Exception as e:
        return HTTPException(status_code=500, detail=f"{e}")


@router.post("/", response_model=AisleDetailWriteOutput, status_code=201)
def create_aisle(aisle_input: AisleInput, session: Session = Depends(get_session)):
    """
    Create a new aisle.

    building_id and module_id may not both be set. Only one allowed.
    """

    # Validate the input data
    if not aisle_input or not isinstance(aisle_input, AisleInput):
        return HTTPException(status_code=400, detail="Aisle data is required")

    # Create a new Aisle object
    new_aisle = Aisle(**aisle_input.model_dump())

    try:
        session.add(new_aisle)
        session.commit()
        session.refresh(new_aisle)

        return new_aisle

    except Exception as e:
        return HTTPException(status_code=500, detail=f"{e}")


@router.patch("/{id}", response_model=AisleDetailWriteOutput)
def update_aisle(id: int, aisle: AisleInput, session: Session = Depends(get_session)):
    """
    Update an existing aisle.
    """
    # Check if the ID is provided and is an integer
    if not id or not isinstance(id, int):
        return HTTPException(status_code=404, detail="Aisle ID is required")

    # Validate the input data
    if not aisle:
        return HTTPException(status_code=400, detail="Aisle data is required")

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
    Delete an aisle by its id.
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
