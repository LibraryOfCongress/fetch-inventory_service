"""Audit log add id and add triggers

Revision ID: 2025_04_10_11:51:05
Revises: 2025_04_09_09:43:23
Create Date: 2025-04-10 15:51:05.002058

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2025_04_10_11:51:05'
down_revision: Union[str, None] = '2025_04_09_09:43:23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_log",
        sa.Column("updated_by_user_id", sa.VARCHAR(50), nullable=True, default=None),
    )
    sql = """
            CREATE OR REPLACE FUNCTION audit_trigger() RETURNS TRIGGER AS $$
            DECLARE
                new_data jsonb;
                old_data jsonb;
                key text;
                new_values jsonb;
                old_values jsonb;
                user_name text;
                updated_by_user_id text;
            BEGIN

                user_name := current_setting('audit.user_name', true);
                updated_by_user_id := current_setting('audit.user_id', true);

                IF user_name IS NULL THEN
                    user_name := current_user;
                END IF;

                IF updated_by_user_id IS NULL THEN
                    updated_by_user_id := '0';
                END IF;

                new_values := '{}';
                old_values := '{}';

                IF TG_OP = 'INSERT' THEN
                    new_data := to_jsonb(NEW);
                    new_values := new_data;

                ELSIF TG_OP = 'UPDATE' THEN
                    new_data := to_jsonb(NEW);
                    old_data := to_jsonb(OLD);

                    FOR key IN SELECT jsonb_object_keys(new_data) INTERSECT SELECT jsonb_object_keys(old_data)
                    LOOP
                        IF new_data ->> key != old_data ->> key THEN
                            new_values := new_values || jsonb_build_object(key, new_data ->> key);
                            old_values := old_values || jsonb_build_object(key, old_data ->> key);
                        END IF;
                    END LOOP;

                ELSIF TG_OP = 'DELETE' THEN
                    old_data := to_jsonb(OLD);
                    old_values := old_data;

                    FOR key IN SELECT jsonb_object_keys(old_data)
                    LOOP
                        old_values := old_values || jsonb_build_object(key, old_data ->> key);
                    END LOOP;

                END IF;

                IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
                    INSERT INTO audit_log (table_name, record_id, operation_type, updated_by, original_values, new_values, updated_by_user_id)
                    VALUES (TG_TABLE_NAME, NEW.id, TG_OP, user_name, old_values, new_values, updated_by_user_id);

                    RETURN NEW;
                ELSE
                    INSERT INTO audit_log (table_name, record_id, operation_type, updated_by, original_values, new_values, updated_by_user_id)
                    VALUES (TG_TABLE_NAME, OLD.id, TG_OP, user_name, old_values, new_values, updated_by_user_id);

                    RETURN OLD;
                END IF;
            END;
            $$ LANGUAGE plpgsql;
        """
    op.execute(sql)
    sql = """
            CREATE TRIGGER audit_log_trigger_items
                BEFORE UPDATE
             ON public.items
                FOR EACH ROW
                WHEN (old.scanned_for_accession IS DISTINCT FROM new.scanned_for_accession OR
                old.scanned_for_verification IS DISTINCT FROM new.scanned_for_verification OR
                old.scanned_for_refile_queue IS DISTINCT FROM new.scanned_for_refile_queue OR
                old.status IS DISTINCT FROM new.status)
                EXECUTE FUNCTION audit_trigger();

            CREATE TRIGGER audit_log_trigger_non_tray_items
                BEFORE UPDATE
             ON public.non_tray_items
                FOR EACH ROW
                WHEN (old.scanned_for_accession IS DISTINCT FROM new.scanned_for_accession OR
                old.scanned_for_verification IS DISTINCT FROM new.scanned_for_verification OR
                old.scanned_for_shelving IS DISTINCT FROM new.scanned_for_shelving OR
                old.scanned_for_refile_queue IS DISTINCT FROM new.scanned_for_refile_queue OR
                old.status IS DISTINCT FROM new.status OR
                old.shelf_position_id IS DISTINCT FROM new.shelf_position_id)
                EXECUTE FUNCTION audit_trigger();

            CREATE TRIGGER audit_log_trigger_trays
                BEFORE UPDATE
             ON public.trays
                FOR EACH ROW
                WHEN (old.scanned_for_accession IS DISTINCT FROM new.scanned_for_accession OR
                old.scanned_for_verification IS DISTINCT FROM new.scanned_for_verification OR
                old.scanned_for_shelving IS DISTINCT FROM new.scanned_for_shelving OR
                old.shelf_position_id IS DISTINCT FROM new.shelf_position_id)
                EXECUTE FUNCTION audit_trigger();

        """
    op.execute(sql)


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    sql = """
               DROP TRIGGER audit_log_trigger_items on items;
               DROP TRIGGER audit_log_trigger_non_tray_items on non_tray_items;
               DROP TRIGGER audit_log_trigger_trays on trays;
           """
    op.execute(sql)
    op.drop_column("audit_log", "updated_by_user_id")
