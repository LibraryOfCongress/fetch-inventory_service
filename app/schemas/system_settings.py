# /code/app/schemas/system_settings.py

from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class SystemSettingInput(BaseModel):
    """Schema for creating a new system setting."""
    key: str
    value: str
    description: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "shelf_position_auto_assign_direction",
                "value": "low_to_high",
                "description": "Direction for auto-assigning shelf positions"
            }
        }
    )


class SystemSettingUpdateInput(BaseModel):
    """Schema for updating an existing system setting."""
    value: str
    description: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "value": "high_to_low",
                "description": "Updated description"
            }
        }
    )


class SystemSettingOutput(BaseModel):
    """Schema for system setting output."""
    id: int
    key: str
    value: str
    description: Optional[str] = None
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(from_attributes=True)
