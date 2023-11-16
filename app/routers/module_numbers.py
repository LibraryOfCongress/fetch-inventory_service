from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.models.module_numbers import ModuleNumber
from app.schemas.module_numbers import (
    ModuleNumberInput,
    ModuleNumberListOutput,
    ModuleNumberDetailOutput,
)


router = APIRouter(
    prefix="/modules",
    tags=["modules"],
)


@router.get("/numbers", response_model=list[ModuleNumberListOutput])
def get_module_number_list(session: Session = Depends(get_session)) -> list:
    query = select(ModuleNumber)
    return session.exec(query).all()


@router.get("/numbers/{id}", response_model=ModuleNumberDetailOutput)
def get_module_number_detail(id: int, session: Session = Depends(get_session)):
    module_number = session.get(ModuleNumber, id)
    if module_number:
        return module_number
    else:
        raise HTTPException(status_code=404)


@router.post("/numbers", response_model=ModuleNumberDetailOutput, status_code=201)
def create_module_number(
    module_number_input: ModuleNumberInput, session: Session = Depends(get_session)
) -> ModuleNumber:
    """
    Create a module number:

    - **number**: Required unique integer that represents a module number
    """
    try:
        new_module_number = ModuleNumber(**module_number_input.model_dump())
        session.add(new_module_number)
        session.commit()
        session.refresh(new_module_number)
        return new_module_number
    except IntegrityError as e:
        raise HTTPException(status_code=422, detail=f"{e}")


@router.patch("/numbers/{id}", response_model=ModuleNumberDetailOutput)
def update_module_number(
    id: int, module_number: ModuleNumberInput, session: Session = Depends(get_session)
):
    try:
        existing_module_number = session.get(ModuleNumber, id)
        if not existing_module_number:
            raise HTTPException(status_code=404)
        mutated_data = module_number.model_dump(exclude_unset=True)
        for key, value in mutated_data.items():
            setattr(existing_module_number, key, value)
        setattr(existing_module_number, "update_dt", datetime.utcnow())
        session.add(existing_module_number)
        session.commit()
        session.refresh(existing_module_number)
        return existing_module_number
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.delete("/numbers/{id}", status_code=204)
def delete_module_number(id: int, session: Session = Depends(get_session)):
    module_number = session.get(ModuleNumber, id)
    if module_number:
        session.delete(module_number)
        session.commit()
    else:
        raise HTTPException(status_code=404)
