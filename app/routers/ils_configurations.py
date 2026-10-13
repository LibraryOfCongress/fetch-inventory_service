import uuid
from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone

from app.database.session import get_session
from app.models.ils_configurations import ILSConfiguration
from app.schemas.ils_configurations import (
    ILSConfigurationInput,
    ILSConfigurationUpdateInput,
    ILSConfigurationListOutput,
    ILSConfigurationDetailOutput,
)
from app.config.exceptions import NotFound, ValidationException
from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/ils-configurations",
    tags=["ils configurations"],
    dependencies=[Depends(RequiresPermission("can_manage_system_configurations"))],
)

@router.get("/", response_model=List[ILSConfigurationListOutput])
def get_ils_configurations(session: Session = Depends(get_session)) -> List[ILSConfiguration]:
    """
    Get all ILS configurations.
    """
    statement = select(ILSConfiguration)
    configs = session.execute(statement).scalars().all()
    return list(configs)


@router.get("/{config_id}", response_model=ILSConfigurationDetailOutput)
def get_ils_configuration_by_id(config_id: uuid.UUID, session: Session = Depends(get_session)) -> ILSConfiguration:
    """
    Get an ILS configuration by its UUID.
    """
    statement = select(ILSConfiguration).where(ILSConfiguration.id == config_id)
    config = session.execute(statement).scalars().first()
    
    if not config:
        raise NotFound(detail=f"ILS Configuration '{config_id}' not found")
    
    return config


@router.post("/", response_model=ILSConfigurationDetailOutput, status_code=201)
def create_ils_configuration(
    config_input: ILSConfigurationInput,
    session: Session = Depends(get_session)
) -> ILSConfiguration:
    """
    Create a new ILS configuration.
    """
    existing = session.execute(
        select(ILSConfiguration).where(ILSConfiguration.name == config_input.name)
    ).scalars().first()
    
    if existing:
        raise ValidationException(detail=f"ILS Configuration with name '{config_input.name}' already exists")
    
    new_config = ILSConfiguration(**config_input.model_dump())
    new_config.create_dt = datetime.now(timezone.utc)
    new_config.update_dt = datetime.now(timezone.utc)
    
    session.add(new_config)
    session.commit()
    session.refresh(new_config)
    
    return new_config


@router.patch("/{config_id}", response_model=ILSConfigurationDetailOutput)
def update_ils_configuration(
    config_id: uuid.UUID,
    config_input: ILSConfigurationUpdateInput,
    session: Session = Depends(get_session)
) -> ILSConfiguration:
    """
    Update an ILS configuration by its UUID.
    """
    statement = select(ILSConfiguration).where(ILSConfiguration.id == config_id)
    config = session.execute(statement).scalars().first()
    
    if not config:
        raise NotFound(detail=f"ILS Configuration '{config_id}' not found")
    
    # Optional unique name check
    if config_input.name and config_input.name != config.name:
        existing = session.execute(
            select(ILSConfiguration).where(ILSConfiguration.name == config_input.name)
        ).scalars().first()
        if existing:
            raise ValidationException(detail=f"ILS Configuration with name '{config_input.name}' already exists")
            
    # Update fields
    for field, value in config_input.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    
    config.update_dt = datetime.now(timezone.utc)
    session.add(config)
    session.commit()
    session.refresh(config)
    
    return config


@router.delete("/{config_id}")
def delete_ils_configuration(config_id: uuid.UUID, session: Session = Depends(get_session)):
    """
    Delete an ILS configuration by its UUID.
    """
    statement = select(ILSConfiguration).where(ILSConfiguration.id == config_id)
    config = session.execute(statement).scalars().first()
    
    if not config:
        raise NotFound(detail=f"ILS Configuration '{config_id}' not found")
        
    # Validation constraint: verify nothing is linked
    if config.owners:
         raise ValidationException(detail=f"Cannot delete config '{config_id}' because it acts as the primary configuration for {len(config.owners)} owner(s). Reassign them first.")
    
    session.delete(config)
    session.commit()
    
    return {"detail": f"ILS Configuration '{config_id}' deleted successfully"}


from pydantic import BaseModel
class SyncRequestsInput(BaseModel):
    config_ids: List[uuid.UUID]

@router.post("/sync-requests", status_code=202)
def sync_ils_requests(
    payload: SyncRequestsInput,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Trigger a background sync of ILS requests for the given configurations.
    """
    from app.ils.tasks import sync_requests_async
    
    triggered_count = 0
    for config_id in payload.config_ids:
        # Validate existence and state
        config = session.get(ILSConfiguration, config_id)
        if config and config.is_active and config.enable_requests_hook:
            background_tasks.add_task(sync_requests_async, config_id)
            triggered_count += 1
            
    return {"detail": f"Triggered {triggered_count} ILS sync tasks asynchronously."}
