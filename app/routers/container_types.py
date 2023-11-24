from fastapi import APIRouter, HTTPException, Depends, Response
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.container_types import ContainerType

from app.schemas.container_types import (
    ContainerTypeInput,
    ContainerTypeListOutput,
    ContainerTypeDetailWriteOutput,
    ContainerTypeDetailReadOutput,
)

router = APIRouter(
    prefix="/container-types",
    tags=["container types"],
)


@router.get("/", response_model=Page[ContainerTypeListOutput])
def get_container_type_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a list of container types
    """
    return paginate(session, select(ContainerType))


@router.get("/{id}", response_model=ContainerTypeDetailReadOutput)
def get_container_type_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a container type by its ID.
    """
    container_type = session.get(ContainerType, id)
    if container_type is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return container_type


@router.post("/", response_model=ContainerTypeDetailWriteOutput, status_code=201)
def create_container_type(container_type_input: ContainerTypeInput, session: Session = Depends(get_session)):
    """
    Create a new container type record.

    **type**: Required varchar 25
    """
    new_container_type = ContainerType(**container_type_input.model_dump())

    session.add(new_container_type)
    session.commit()
    session.refresh(new_container_type)

    return new_container_type


@router.patch("/{id}", response_model=ContainerTypeDetailWriteOutput)
def update_container_type(id: int, container_type: ContainerTypeInput, session: Session = Depends(get_session)):
    """
    Update a container type record by its id.
    """
    existing_container_type = session.get(ContainerType, id)

    if not existing_container_type:
        raise HTTPException(status_code=404, detail="Not found")

    mutated_data = container_type.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_container_type, key, value)

    setattr(existing_container_type, "update_dt", datetime.utcnow())

    session.add(existing_container_type)
    session.commit()
    session.refresh(existing_container_type)
    return existing_container_type


@router.delete("/{id}", status_code=204)
def delete_container_type(id: int, session: Session = Depends(get_session)):
    """
    Delete a container type by its ID.
    """
    container_type = session.get(ContainerType, id)
    if container_type:
        session.delete(container_type)
        session.commit()
    else:
        raise HTTPException(status_code=404)
