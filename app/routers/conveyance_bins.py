from fastapi import APIRouter, HTTPException, Depends, Response
from sqlmodel import Session, select
from datetime import datetime
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.conveyance_bins import ConveyanceBin

from app.schemas.conveyance_bins import (
    ConveyanceBinInput,
    ConveyanceBinListOutput,
    ConveyanceBinDetailWriteOutput,
    ConveyanceBinDetailReadOutput,
)

router = APIRouter(
    prefix="/conveyance-bins",
    tags=["conveyance bins"],
)


@router.get("/", response_model=Page[ConveyanceBinListOutput])
def get_conveyance_bin_list(session: Session = Depends(get_session)) -> list:
    """
    Retrieve a list of conveyance bins
    """
    return paginate(session, select(ConveyanceBin))


@router.get("/{id}", response_model=ConveyanceBinDetailReadOutput)
def get_conveyance_bin_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the details of a conveyance bin by its ID.
    """
    conveyance_bin = session.get(ConveyanceBin, id)
    if conveyance_bin is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return conveyance_bin


@router.post("/", response_model=ConveyanceBinDetailWriteOutput, status_code=201)
def create_conveyance_bin(conveyance_bin_input: ConveyanceBinInput, session: Session = Depends(get_session)):
    """
    Create a new conveyance bin record
    """
    new_conveyance_bin = ConveyanceBin(**conveyance_bin_input.model_dump())

    session.add(new_conveyance_bin)
    session.commit()
    session.refresh(new_conveyance_bin)

    return new_conveyance_bin


@router.patch("/{id}", response_model=ConveyanceBinDetailWriteOutput)
def update_conveyance_bin(id: int, conveyance_bin: ConveyanceBinInput, session: Session = Depends(get_session)):
    """
    Update a conveyance bin record by its id
    """
    existing_conveyance_bin = session.get(ConveyanceBin, id)

    if not existing_conveyance_bin:
        raise HTTPException(status_code=404, detail="Not found")

    mutated_data = conveyance_bin.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_conveyance_bin, key, value)

    setattr(existing_conveyance_bin, "update_dt", datetime.utcnow())

    session.add(existing_conveyance_bin)
    session.commit()
    session.refresh(existing_conveyance_bin)
    return existing_conveyance_bin


@router.delete("/{id}", status_code=204)
def delete_conveyance_bin(id: int, session: Session = Depends(get_session)):
    """
    Delete a conveyance bin by its ID
    """
    conveyance_bin = session.get(ConveyanceBin, id)
    if conveyance_bin:
        session.delete(conveyance_bin)
        session.commit()
    else:
        raise HTTPException(status_code=404)
