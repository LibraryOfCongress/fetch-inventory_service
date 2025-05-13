"""audit_log_hotfix

Revision ID: 2025_03_04_13:23:59
Revises: 2025_02_23_15:11:21
Create Date: 2025-03-04 13:23:59.948040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '2025_03_04_13:23:59'
down_revision: Union[str, None] = '2025_02_23_15:11:21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Ensure audit_log.id is an auto-incrementing primary key
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'audit_log' AND column_name = 'id'
            ) THEN
                ALTER TABLE audit_log ADD COLUMN id BIGSERIAL PRIMARY KEY;
            ELSE
                ALTER TABLE audit_log ALTER COLUMN id SET DEFAULT nextval('audit_log_id_seq');
            END IF;
        END $$;
    """)
    
    # Update the trigger function to avoid duplicate primary key issues
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_trigger() RETURNS TRIGGER AS $$
        DECLARE
            new_data jsonb;
            old_data jsonb;
            key text;
            new_values jsonb;
            old_values jsonb;
            user_id text;
        BEGIN
            user_id := current_setting('audit.user_id', true);
            IF user_id IS NULL THEN
                user_id := current_user;
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

            INSERT INTO audit_log (table_name, record_id, operation_type, updated_by, original_values, new_values)
            VALUES (TG_TABLE_NAME, COALESCE(NEW.id, OLD.id), TG_OP, user_id, old_values, new_values)
            RETURNING id;

            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)

def downgrade():
    op.execute("DROP FUNCTION audit_trigger;")
