"""Add Trigger To Tables

Revision ID: 2024_07_31_20:51:58
Revises: 2024_07_31_20:45:18
Create Date: 2024-08-01 00:51:58.797996

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2024_07_31_20:51:58'
down_revision: Union[str, None] = '2024_07_31_20:45:18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sql = """
        CREATE TRIGGER audit_log_trigger_accession_jobs
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.accession_jobs
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_aisle_numbers
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.aisle_numbers
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_aisles
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.aisles
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();

        CREATE TRIGGER audit_log_trigger_barcode_types
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.barcode_types
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_barcodes
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.barcodes
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_batch_uploads
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.batch_uploads
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_buildings
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.buildings
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_container_types
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.container_types
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_conveyance_bins
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.conveyance_bins
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_delivery_locations
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.delivery_locations
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_group_permissions
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.group_permissions
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_item_withdrawals
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.item_withdrawals
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_items
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.items
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_ladder_numbers
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.ladder_numbers
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_ladders
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.ladders
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_media_types
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.media_types
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_modules
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.modules
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_non_tray_item_withdrawals
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.non_tray_item_withdrawals
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_non_tray_items
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.non_tray_items
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_owner_tiers
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.owner_tiers
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_owners
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.owners
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();

        CREATE TRIGGER audit_log_trigger_permissions
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.permissions
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_pick_lists
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.pick_lists
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_priorities
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.priorities
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_refile_items
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.refile_items
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_refile_jobs
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.refile_jobs
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_refile_non_tray_items
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.refile_non_tray_items
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_request_types
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.request_types
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_requests
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.requests
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_shelf_numbers
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.shelf_numbers
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_shelf_position_numbers
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.shelf_position_numbers
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_shelf_positions
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.shelf_positions
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_shelves
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.shelves
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_shelving_jobs
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.shelving_jobs
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_side_orientations
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.side_orientations
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_sides
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.sides
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_size_class
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.size_class
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_subcollections
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.subcollections
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_tray_withdrawals
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.tray_withdrawals
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_trays
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.trays
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_user_groups
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.user_groups
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_users
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.users
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_verification_jobs
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.verification_jobs
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();


        CREATE TRIGGER audit_log_trigger_withdraw_jobs
            BEFORE INSERT OR UPDATE OR DELETE
         ON public.withdraw_jobs
            FOR EACH ROW
            EXECUTE FUNCTION audit_trigger();
    """
    op.execute(sql)


def downgrade() -> None:
    sql = """
        DROP TRIGGER audit_log_trigger_accession_jobs on accession_jobs;
        DROP TRIGGER audit_log_trigger_aisle_numbers on aisle_numbers;
        DROP TRIGGER audit_log_trigger_aisles on aisles;
        DROP TRIGGER audit_log_trigger_barcode_types on barcode_types;
        DROP TRIGGER audit_log_trigger_barcodes on barcodes;
        DROP TRIGGER audit_log_trigger_batch_uploads on batch_uploads;
        DROP TRIGGER audit_log_trigger_buildings on buildings;
        DROP TRIGGER audit_log_trigger_container_types on container_types;
        DROP TRIGGER audit_log_trigger_conveyance_bins on conveyance_bins;
        DROP TRIGGER audit_log_trigger_delivery_locations on delivery_locations;
        DROP TRIGGER audit_log_trigger_group_permissions on group_permissions;
        DROP TRIGGER audit_log_trigger_item_withdrawals on item_withdrawals;
        DROP TRIGGER audit_log_trigger_items on items;
        DROP TRIGGER audit_log_trigger_ladder_numbers on ladder_numbers;
        DROP TRIGGER audit_log_trigger_ladders on ladders;
        DROP TRIGGER audit_log_trigger_media_types on media_types;
        DROP TRIGGER audit_log_trigger_modules on modules;
        DROP TRIGGER audit_log_trigger_non_tray_item_withdrawals on non_tray_item_withdrawals;
        DROP TRIGGER audit_log_trigger_non_tray_items on non_tray_items;
        DROP TRIGGER audit_log_trigger_owner_tiers on owner_tiers;
        DROP TRIGGER audit_log_trigger_owners on owners;
        DROP TRIGGER audit_log_trigger_permissions on permissions;
        DROP TRIGGER audit_log_trigger_pick_lists on pick_lists;
        DROP TRIGGER audit_log_trigger_priorities on priorities;
        DROP TRIGGER audit_log_trigger_refile_items on refile_items;
        DROP TRIGGER audit_log_trigger_refile_jobs on refile_jobs;
        DROP TRIGGER audit_log_trigger_refile_non_tray_items on refile_non_tray_items;
        DROP TRIGGER audit_log_trigger_request_types on request_types;
        DROP TRIGGER audit_log_trigger_requests on requests;
        DROP TRIGGER audit_log_trigger_shelf_numbers on shelf_numbers;
        DROP TRIGGER audit_log_trigger_shelf_position_numbers on shelf_position_numbers;
        DROP TRIGGER audit_log_trigger_shelf_positions on shelf_positions;
        DROP TRIGGER audit_log_trigger_shelves on shelves;
        DROP TRIGGER audit_log_trigger_shelving_jobs on shelving_jobs;
        DROP TRIGGER audit_log_trigger_side_orientations on side_orientations;
        DROP TRIGGER audit_log_trigger_sides on sides;
        DROP TRIGGER audit_log_trigger_size_class on size_class;
        DROP TRIGGER audit_log_trigger_subcollections on subcollections;
        DROP TRIGGER audit_log_trigger_tray_withdrawals on tray_withdrawals;
        DROP TRIGGER audit_log_trigger_trays on trays;
        DROP TRIGGER audit_log_trigger_user_groups on user_groups;
        DROP TRIGGER audit_log_trigger_users on users;
        DROP TRIGGER audit_log_trigger_verification_jobs on verification_jobs;
        DROP TRIGGER audit_log_trigger_withdraw_jobs on withdraw_jobs;
    """
    op.execute(sql)
