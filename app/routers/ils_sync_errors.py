from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from app.database.session import get_session
from app.models.ils_sync_errors import ILSSyncError, ILSSyncStatusEnum, WorkflowActionEnum
from app.schemas.ils_sync_errors import ILSSyncErrorListOutput
from app.auth.dependencies import RequiresPermission, get_current_user_with_permissions
from app.models.users import User

from app.ils.tasks import validate_accessioned_item_async
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.barcodes import Barcode

router = APIRouter(
    prefix="/ils-sync-errors",
    tags=["ils sync errors"],
    dependencies=[Depends(RequiresPermission("can_manage_system_configurations"))],
)

@router.get("/", response_model=Page[ILSSyncErrorListOutput])
def get_sync_errors(
    status: ILSSyncStatusEnum = ILSSyncStatusEnum.ACTIVE,
    session: Session = Depends(get_session)
):
    query = select(ILSSyncError).where(ILSSyncError.status == status).order_by(ILSSyncError.created_at.desc())
    return paginate(session, query)


@router.patch("/{id}/resolve", status_code=200)
def resolve_sync_error(
    id: uuid.UUID, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions)
):
    error_log = session.get(ILSSyncError, id)
    if not error_log:
        raise HTTPException(status_code=404, detail="Sync error not found")

    error_log.status = ILSSyncStatusEnum.RESOLVED
    error_log.resolved_by_user_id = current_user.id
    error_log.resolved_at = datetime.now(timezone.utc)
    
    session.add(error_log)
    session.commit()
    return {"status": "ok", "message": "Resolved"}


@router.post("/{id}/retry", status_code=200)
def retry_sync_error(
    id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_with_permissions)
):
    error_log = session.get(ILSSyncError, id)
    if not error_log:
        raise HTTPException(status_code=404, detail="Sync error not found")
        
    if error_log.workflow_action == WorkflowActionEnum.ACCESSION:
        # Determine if it's an Item or NonTrayItem
        item = session.execute(
            select(Item).join(Barcode, Item.barcode_id == Barcode.id).filter(Barcode.value == error_log.item_barcode)
        ).scalars().first()
        
        non_tray_item = session.execute(
            select(NonTrayItem).join(Barcode, NonTrayItem.barcode_id == Barcode.id).filter(Barcode.value == error_log.item_barcode)
        ).scalars().first()
        
        if item:
             background_tasks.add_task(
                 validate_accessioned_item_async,
                 barcode_value=error_log.item_barcode,
                 owner_id=item.owner_id,
                 is_non_tray=False
             )
        elif non_tray_item:
             background_tasks.add_task(
                 validate_accessioned_item_async,
                 barcode_value=error_log.item_barcode,
                 owner_id=non_tray_item.owner_id,
                 is_non_tray=True
             )
        else:
             raise HTTPException(status_code=400, detail="Cannot find target item in database to retry.")
             
        error_log.status = ILSSyncStatusEnum.RESOLVED
        error_log.resolved_by_user_id = current_user.id
        error_log.resolved_at = datetime.now(timezone.utc)
        session.add(error_log)
        session.commit()
        
        return {"status": "ok", "message": "Retry background task spawned."}
    
    # Catch-all for others added later
    raise HTTPException(status_code=400, detail="Retry not implemented for this workflow action yet.")

