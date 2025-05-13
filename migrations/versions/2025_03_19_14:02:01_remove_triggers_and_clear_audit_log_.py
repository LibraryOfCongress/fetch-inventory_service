"""Remove triggers and clear audit_log table

Revision ID: 2025_03_19_14:02:01
Revises: 2025_03_04_18:05:54
Create Date: 2025-03-19 18:02:01.439452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '2025_03_19_14:02:01'
down_revision: Union[str, None] = '2025_03_17_14:15:08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    # deleting would take to long
    op.drop_table('audit_log')
    op.create_table(
        'audit_log',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('table_name', sa.String(50), nullable=False),
        sa.Column('record_id', sa.String(50), nullable=False),
        sa.Column('operation_type', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_by', sa.String(50), nullable=False),
        sa.Column('original_values', sa.JSON(), nullable=False),
        sa.Column('new_values', sa.JSON(), nullable=False),
        sa.Column("last_action", sa.VARCHAR(length=150), nullable=True, default=None)
    )
    sql = """
            CREATE TRIGGER audit_log_trigger_accession_jobs
                BEFORE INSERT OR UPDATE OR DELETE
             ON public.accession_jobs
                FOR EACH ROW
                EXECUTE FUNCTION audit_trigger();


            CREATE TRIGGER audit_log_trigger_pick_lists
                BEFORE INSERT OR UPDATE OR DELETE
             ON public.pick_lists
                FOR EACH ROW
                EXECUTE FUNCTION audit_trigger();


            CREATE TRIGGER audit_log_trigger_refile_jobs
                BEFORE INSERT OR UPDATE OR DELETE
             ON public.refile_jobs
                FOR EACH ROW
                EXECUTE FUNCTION audit_trigger();


            CREATE TRIGGER audit_log_trigger_shelving_jobs
                BEFORE INSERT OR UPDATE OR DELETE
             ON public.shelving_jobs
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
    sql = """
        CREATE INDEX audit_lookup ON audit_log (record_id, table_name);
        """
    op.execute(sql)


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # apply  2024_07_31_20:51:58_add_trigger_to_tables.py if you want all triggers back

