
import sys
import json
import os
from sqlalchemy.orm import Session
from app.seed.seeder_session import get_session
from app.models.groups import Group
from app.models.users import User
from app.models.accession_jobs import AccessionJob
from app.models.verification_jobs import VerificationJob
from app.models.shelving_jobs import ShelvingJob
from app.models.shelving_job_containers import ShelvingJobContainer
from app.models.requests import Request
from app.models.pick_lists import PickList
from app.models.refile_jobs import RefileJob
from app.models.batch_upload import BatchUpload
from app.models.verification_changes import VerificationChange
from app.models.workflows import Workflow
from app.models.move_discrepancies import MoveDiscrepancy
from app.models.owner_delivery_locations import OwnerDeliveryLocation
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.models.item_retrieval_events import ItemRetrievalEvent
from app.models.non_tray_item_retrieval_events import NonTrayItemRetrievalEvent
from app.models.shelves import Shelf
from app.models.barcodes import Barcode
from app.models.permissions import Permission
from app.models.shipping_jobs import ShippingJob
from app.models.shipping_bins import ShippingBin
from app.logger import migration_logger

def seed_new_permissions():
    print("Starting ad-hoc permission seeder...")
    session = get_session()
    
    # Load JSON
    # Load JSON
    # Path relative to this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'fixtures', 'types', 'client_permissions.json')
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r') as f:
        json_content = json.load(f)
        perms_data = json_content['data']
    
    # Get existing permissions
    try:
        existing_perms = session.query(Permission).all()
        existing_names = {p.name for p in existing_perms}
    except Exception as e:
        print(f"Error querying existing permissions: {e}")
        return
    
    new_perms_count = 0
    for p_data in perms_data:
        if p_data['name'] not in existing_names:
            print(f"Adding new permission: {p_data['name']}")
            new_perm = Permission(
                name=p_data['name'],
                description=p_data['description'],
                # Add status if model requires it, usually defaults are ok
            )
            session.add(new_perm)
            new_perms_count += 1
    
    if new_perms_count > 0:
        print(f"Committing {new_perms_count} new permissions...")
        try:
            session.commit()
            print("Success!")
        except Exception as e:
            print(f"Error committing: {e}")
            session.rollback()
    else:
        print("No new permissions to add.")

if __name__ == "__main__":
    seed_new_permissions()
