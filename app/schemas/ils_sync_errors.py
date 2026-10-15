import uuid
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timezone

from app.models.ils_sync_errors import WorkflowActionEnum, ILSSyncStatusEnum

class ILSSyncErrorInput(BaseModel):
    item_barcode: str
    workflow_action: WorkflowActionEnum
    error_message: str

class ILSSyncErrorUpdateInput(BaseModel):
    status: ILSSyncStatusEnum
    resolved_by_user_id: Optional[int] = None
    resolved_at: Optional[datetime] = None

class ILSSyncErrorBaseOutput(BaseModel):
    id: uuid.UUID
    item_barcode: str
    workflow_action: WorkflowActionEnum
    error_message: str
    status: ILSSyncStatusEnum
    resolved_by_user_id: Optional[int] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

class ILSSyncErrorListOutput(ILSSyncErrorBaseOutput):
    pass

class ILSSyncErrorDetailOutput(ILSSyncErrorBaseOutput):
    pass
