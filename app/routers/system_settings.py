# /code/app/routers/system_settings.py

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone

from app.database.session import get_session
from app.models.system_settings import SystemSetting
from app.schemas.system_settings import (
    SystemSettingInput,
    SystemSettingUpdateInput,
    SystemSettingOutput,
)
from app.config.exceptions import NotFound, ValidationException

from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions

router = APIRouter(
    prefix="/system-settings",
    tags=["system settings"],
    dependencies=[Depends(get_current_user_with_permissions)],
)


@router.get("/", response_model=List[SystemSettingOutput])
def get_system_settings(session: Session = Depends(get_session)) -> List[SystemSetting]:
    """
    Get all system settings.
    """
    statement = select(SystemSetting)
    settings = session.execute(statement).scalars().all()
    return list(settings)


@router.get("/{key}", response_model=SystemSettingOutput)
def get_system_setting_by_key(key: str, session: Session = Depends(get_session)) -> SystemSetting:
    """
    Get a system setting by its key.
    """
    statement = select(SystemSetting).where(SystemSetting.key == key)
    setting = session.execute(statement).scalars().first()
    
    if not setting:
        raise NotFound(detail=f"System setting with key '{key}' not found")
    
    return setting


@router.post("/", response_model=SystemSettingOutput, status_code=201, dependencies=[Depends(RequiresPermission("can_manage_system_configurations"))])
def create_system_setting(
    setting_input: SystemSettingInput,
    session: Session = Depends(get_session)
) -> SystemSetting:
    """
    Create a new system setting.
    """
    # Check if key already exists
    existing = session.execute(
        select(SystemSetting).where(SystemSetting.key == setting_input.key)
    ).scalars().first()
    
    if existing:
        raise ValidationException(detail=f"System setting with key '{setting_input.key}' already exists")
    
    new_setting = SystemSetting(**setting_input.model_dump())
    session.add(new_setting)
    session.commit()
    session.refresh(new_setting)
    
    return new_setting


@router.patch("/{key}", response_model=SystemSettingOutput, dependencies=[Depends(RequiresPermission("can_manage_system_configurations"))])
def update_system_setting(
    key: str,
    setting_input: SystemSettingUpdateInput,
    session: Session = Depends(get_session)
) -> SystemSetting:
    """
    Update a system setting by its key.
    """
    statement = select(SystemSetting).where(SystemSetting.key == key)
    setting = session.execute(statement).scalars().first()
    
    if not setting:
        raise NotFound(detail=f"System setting with key '{key}' not found")
    
    # Update fields
    for field, value in setting_input.model_dump(exclude_unset=True).items():
        setattr(setting, field, value)
    
    setting.update_dt = datetime.now(timezone.utc)
    session.add(setting)
    session.commit()
    session.refresh(setting)
    
    return setting


@router.delete("/{key}", dependencies=[Depends(RequiresPermission("can_manage_system_configurations"))])
def delete_system_setting(key: str, session: Session = Depends(get_session)):
    """
    Delete a system setting by its key.
    """
    statement = select(SystemSetting).where(SystemSetting.key == key)
    setting = session.execute(statement).scalars().first()
    
    if not setting:
        raise NotFound(detail=f"System setting with key '{key}' not found")
    
    session.delete(setting)
    session.commit()
    
    return {"detail": f"System setting '{key}' deleted successfully"}


def get_setting_value(session: Session, key: str, default: str = None) -> str:
    """
    Utility function to get a setting value by key.
    Returns the default value if the setting doesn't exist.
    """
    statement = select(SystemSetting).where(SystemSetting.key == key)
    setting = session.execute(statement).scalars().first()
    
    if setting:
        return setting.value
    return default
