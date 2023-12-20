from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.buildings import Building
from app.schemas.buildings import (
    BuildingInput,
    BuildingUpdateInput,
    BuildingListOutput,
    BuildingDetailWriteOutput,
    BuildingDetailReadOutput,
)

# For future circular imports
# https://sqlmodel.tiangolo.com/tutorial/code-structure/#import-only-while-editing-with-type_checking

router = APIRouter(
    prefix="/buildings",
    tags=["buildings"],
)


@router.get("/", response_model=Page[BuildingListOutput])
def get_building_list(session: Session = Depends(get_session)) -> list:
    """
    Get a paginated list of buildings.

    **Returns:**
    - list Building List Output: The paginated list of buildings.
    """
    return paginate(session, select(Building))


@router.get("/{id}", response_model=BuildingDetailReadOutput)
def get_building_detail(id: int, session: Session = Depends(get_session)):
    """
    Get building detail by ID.

    **Args:**
    - id: The ID of the building.

    **Returns:**
    - Building Detail Read Output: The building detail.

    **Raises:**
    - HTTPException: If the building is not found.
    """

    building = session.get(Building, id)
    if building:
        return building
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=BuildingDetailWriteOutput, status_code=201)
def create_building(
    building_input: BuildingInput, session: Session = Depends(get_session)
) -> Building:
    """
    Create a building:

    **Args:**
    - Building Input: The input data for creating the building.

    **Returns:**
    - Building Detail Write Output: The newly created building.
    """
    new_building = Building(**building_input.model_dump())
    session.add(new_building)
    session.commit()
    session.refresh(new_building)
    return new_building


@router.patch("/{id}", response_model=BuildingDetailWriteOutput)
def update_building(
    id: int, building: BuildingUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a building:

    **Args:**
    - id (int): The ID of the building to update.
    - Building Update Input: The updated building data.

    **Returns:**
    - Building Detail Write Output: The updated building.

    **Raises:**
    - HTTPException: If the building with the given ID is not found or if there is an
    internal server error.
    """
    existing_building = session.get(Building, id)

    if existing_building is None:
        print("here")
        raise HTTPException(status_code=404)

    mutated_data = building.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_building, key, value)

    setattr(existing_building, "update_dt", datetime.utcnow())

    session.add(existing_building)
    session.commit()
    session.refresh(existing_building)

    return existing_building


@router.delete("/{id}")
def delete_building(id: int, session: Session = Depends(get_session)):
    """
    Delete a building by ID.

    **Args:**
    - id: The ID of the building to delete.

    **Returns:**
    - None

    **Raises:**
    - HTTPException: If the building with the specified ID is not found.
    """

    building = session.get(Building, id)

    if building:
        session.delete(building)
        session.commit()
        return HTTPException(status_code=204)
    else:
        return HTTPException(status_code=404)

