# /app/models/refile_items.py - FINAL FIX
from typing import TYPE_CHECKING
from app.database.base import Base
from app.models.link_tables import RefileItemTable

if TYPE_CHECKING:
    from app.models.items import Item
    from app.models.refile_jobs import RefileJob

class RefileItem(Base): 
    # Map to the existing Table object. 
    # SQLAlchemy automatically reads 'id', 'item_id', 'refile_job_id', 'create_dt', 'update_dt' from this table.
    __table__ = RefileItemTable