# /app/models/refile_non_tray_items.py - FINAL FIX
from typing import TYPE_CHECKING
from app.database.base import Base
from app.models.link_tables import RefileNonTrayItemTable

if TYPE_CHECKING:
    from app.models.non_tray_items import NonTrayItem
    from app.models.refile_jobs import RefileJob

class RefileNonTrayItem(Base): 
    # Map to the existing Table object.
    __table__ = RefileNonTrayItemTable