from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.tray_size_class import TraySizeClass
from app.schemas.tray_size_class import (
    TraySizeClassInput,
    TraySizeClassUpdateInput,
    TraySizeClassListOutput,
    TraySizeClassDetailWriteOutput,
    TraySizeClassDetailReadOutput,
)


router = APIRouter(
    prefix="/size_class",
    tags=["size class"],
)


@router.get("/", response_model=Page[TraySizeClassListOutput])
def get_tray_size_class_list(session: Session = Depends(get_session)) -> list:
    """
    Get a paginated list of size classes
    """
    # Create a query to select all tray_size_classs from the database
    return paginate(session, select(TraySizeClass))


@router.get("/{id}", response_model=TraySizeClassDetailReadOutput)
def get_tray_size_class_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a size class by its ID.
    """
    tray_size_class = session.get(TraySizeClass, id)
    if tray_size_class:
        return tray_size_class
    else:
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/", response_model=TraySizeClassDetailWriteOutput, status_code=201)
def create_tray_size_class(
    tray_size_class_input: TraySizeClassInput, session: Session = Depends(get_session)
):
    """
    Create a new size class record.
    """

    new_tray_size_class = TraySizeClass(**tray_size_class_input.model_dump())
    session.add(new_tray_size_class)
    session.commit()
    session.refresh(new_tray_size_class)
    return new_tray_size_class


@router.patch("/{id}", response_model=TraySizeClassDetailWriteOutput)
def update_tray_size_class(
    id: int,
    tray_size_class: TraySizeClassUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update a size class record in the database
    """
    # Get the existing tray_size_class record from the database
    existing_tray_size_class = session.get(TraySizeClass, id)

    # Check if the tray_size_class record exists
    if not existing_tray_size_class:
        raise HTTPException(status_code=404, detail="Not Found")

    # Update the tray_size_class record with the mutated data
    mutated_data = tray_size_class.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_tray_size_class, key, value)
    setattr(existing_tray_size_class, "update_dt", datetime.utcnow())

    # Commit the changes to the database
    session.add(existing_tray_size_class)
    session.commit()
    session.refresh(existing_tray_size_class)

    return existing_tray_size_class


@router.delete("/{id}")
def delete_tray_size_class(id: int, session: Session = Depends(get_session)):
    """
    Delete a tray_size_class by its ID
    """
    tray_size_class = session.get(TraySizeClass, id)

    if tray_size_class:
        session.delete(tray_size_class)
        session.commit()
        return HTTPException(status_code=204)
    else:
        raise HTTPException(status_code=404)
