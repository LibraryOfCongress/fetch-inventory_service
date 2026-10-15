# /code/app/helpers/system_setting_helpers.py

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.system_settings import SystemSetting


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
