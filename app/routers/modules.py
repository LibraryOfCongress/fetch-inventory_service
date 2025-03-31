import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams, ModuleFilterParams
from app.models.modules import Module
from app.models.buildings import Building
from app.schemas.modules import (
    ModuleInput,
    ModuleUpdateInput,
    ModuleListOutput,
    ModuleDetailWriteOutput,
    ModuleDetailReadOutput,
)
from app.config.exceptions import NotFound, ValidationException
from app.sorting import BaseSorter

LOGGER = logging.getLogger("router.modules")

router = APIRouter(
    prefix="/modules",
    tags=["modules"],
)


@router.get("/", response_model=Page[ModuleListOutput])
def get_module_list(
    session: Session = Depends(get_session),
    params: ModuleFilterParams = Depends(),
    sort_params: SortParams = Depends(),
    search: Optional[str] = Query(None, description="Search by Module Number"),
) -> list:
    """
    Retrieve a paginated list of modules.

    **Parameters:**
    - building_name (str): The name of the building to filter by.
    - sort_params (SortParams): The sorting parameters.
    - search (Optional[str]): The search query.
        - Number: The number of the module to search for.

    **Returns:**
    - Module List Output: The paginated list of modules.
    """
    # Create a query to select all Module
    query = select(Module).join(Building, Module.building_id == Building.id)

    if search:
        query = query.where(Module.module_number.contains(search))
    if params.building_name:
        query = query.where(Building.name == params.building_name)

    if params.building_id:
        query = query.where(Building.id == params.building_id)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(Module)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=ModuleDetailReadOutput)
def get_module_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve module details by ID.

    **Parameters:**
    - id: The ID of the module to retrieve.

    **Returns:**
    - Module Detail Read Output: The module details.

    **Raises:**
    - HTTPException: If the module with the specified ID is not found.
    """
    module = session.get(Module, id)

    if module:
        return module

    raise NotFound(detail=f"Module ID {id} Not Found")


@router.post("/", response_model=ModuleDetailWriteOutput, status_code=201)
def create_module(
    module_input: ModuleInput, session: Session = Depends(get_session)
) -> Module:
    """
    Create a module:

    **Args:**
    - ModuleInput: Input data for the new module.

    **Returns:**
    - Module: The newly created module.

    **Raises:**
    - HTTPException: If an error occurs during module creation.

    **Notes:**
    - **building_id**: Required integer id for related building
    - **module_number**: Required unique string for each module
    """
    try:
        new_module = Module(**module_input.model_dump())
        session.add(new_module)
        session.commit()
        session.refresh(new_module)

        return new_module

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=ModuleDetailWriteOutput)
def update_module(
    id: int, module: ModuleUpdateInput, session: Session = Depends(get_session)
):
    """
    Update a module by its ID.

    **Args:**
    - id: The ID of the module to update.
    - Module Update Input: The updated module data.

    **Returns:**
    - Module Detail Write Output: The updated module.

    **Raises:**
    - HTTPException: If the module is not found.
    """
    existing_module = session.get(Module, id)

    if not existing_module:
        raise NotFound(detail=f"Module ID {id} Not Found")

    mutated_data = module.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_module, key, value)

    setattr(existing_module, "update_dt", datetime.now(timezone.utc))

    session.add(existing_module)
    session.commit()
    session.refresh(existing_module)

    return existing_module


@router.delete("/{id}")
def delete_module(id: int, session: Session = Depends(get_session)):
    """
    Delete a module by its ID.

    **Args:**
    - id: The ID of the module.

    **Raises:**
    - HTTPException: If the module is not found.

    **Returns:**
    - None
    """
    module = session.get(Module, id)
    if module:
        session.delete(module)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Module ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Module ID {id} Not Found")
