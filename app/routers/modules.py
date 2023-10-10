from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime

from app.database.session import get_session
from app.models.modules import Module
from app.schemas.modules import (
    ModuleInput,
    ModuleListOutput,
    ModuleDetailWriteOutput,
    ModuleDetailReadOutput,
)


router = APIRouter(
    prefix="/modules",
    tags=["modules"],
)


@router.get("/", response_model=list[ModuleListOutput])
def get_module_list(session: Session = Depends(get_session)) -> list:
    query = select(Module)
    return session.exec(query).all()


@router.get("/{id}", response_model=ModuleDetailReadOutput)
def get_module_detail(id: int, session: Session = Depends(get_session)):
    module = session.get(Module, id)
    if module:
        return module
    else:
        raise HTTPException(status_code=404)


@router.post("/", response_model=ModuleDetailWriteOutput)
def create_module(module_input: ModuleInput, session: Session = Depends(get_session)) -> Module:
    """
    Create a module:

    - **building_id**: Required integer id for related building
    - **module_number_id**: Required integer id for related module number
    - **barcode**: Optional uuid for related barcode
    """
    new_module = Module(**module_input.model_dump())
    session.add(new_module)
    session.commit()
    session.refresh(new_module)
    return new_module


@router.patch("/{id}", response_model=ModuleDetailWriteOutput)
def update_module(id: int, module: ModuleInput, session: Session = Depends(get_session)):
    try:
        existing_module = session.get(Module, id)
        if not existing_module:
            raise HTTPException(status_code=404)
        mutated_data = module.model_dump(exclude_unset=True)
        for key, value in mutated_data.items():
            setattr(existing_module, key, value)
        setattr(existing_module, "update_dt", datetime.utcnow())
        session.add(existing_module)
        session.commit()
        session.refresh(existing_module)
        return existing_module
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_module(id: int, session: Session = Depends(get_session)):
    module = session.get(Module, id)
    if module:
        session.delete(module)
        session.commit()
    else:
        raise HTTPException(status_code=404)
