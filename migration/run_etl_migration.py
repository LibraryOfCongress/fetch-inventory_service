import os
import psycopg2
from psycopg2 import extras
import logging
import json
from datetime import datetime

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Connection Strings
SOURCE_DB = os.getenv("SOURCE_DB_URL", "postgresql://postgres:postgres@localhost:5432/lc_baseline_db")
TARGET_DB = os.getenv("TARGET_DB_URL", "postgresql://postgres:postgres@localhost:5432/fetch2_clean_db")

import argparse

# Global stats for the report
migration_errors = []
BATCH_SIZE = 5000 

def migrate_table(src_conn, tgt_cur, table_name, query, transform_fn=None, is_critical=False, limit=None):
    """Migrates a table with optional sampling and fail-fast logic."""
    logger.info(f"Migrating table: {table_name}...")
    
    # Apply sampling limit if provided
    if limit:
        if "WHERE" in query.upper():
            query += f" LIMIT {limit}"
        elif "ORDER BY" in query.upper():
            query += f" LIMIT {limit}"
        else:
            query += f" LIMIT {limit}"

    src_cur = src_conn.cursor(name=f"scroll_{table_name}", cursor_factory=extras.DictCursor)
    
    try:
        src_cur.execute(query)
        total_migrated = 0
        while True:
            rows = src_cur.fetchmany(BATCH_SIZE)
            if not rows:
                break

            cols = [desc[0] for desc in src_cur.description]
            if transform_fn:
                processed_rows = [transform_fn(row, cols) for row in rows]
                cols = list(processed_rows[0].keys())
                data = [tuple(r.values()) for r in processed_rows]
            else:
                data = [tuple(row) for row in rows]

            if total_migrated == 0:
                col_names = ",".join(cols)
                placeholders = ",".join(["%s"] * len(cols))
                insert_query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

            extras.execute_batch(tgt_cur, insert_query, data)
            total_migrated += len(data)
            if total_migrated % 50000 == 0:
                logger.info(f"  ...progress: {total_migrated} rows migrated into {table_name}")

        logger.info(f"  Successfully migrated {total_migrated} total rows into {table_name}.")
        return True

    except Exception as e:
        error_msg = str(e)
        migration_errors.append({"table": table_name, "error": error_msg, "critical": is_critical})
        logger.error(f"  FAILED to migrate {table_name}: {error_msg}")
        
        if is_critical:
            logger.error(f"  CRITICAL TABLE FAILED. Halting migration to prevent cascading errors.")
            raise Exception(f"Migration halted due to critical failure in {table_name}")
        
        return False
    finally:
        src_cur.close()

def run_migration(sample_limit=None):
    src_conn = None
    tgt_conn = None
    
    try:
        src_conn = psycopg2.connect(SOURCE_DB)
        tgt_conn = psycopg2.connect(TARGET_DB)
        tgt_cur = tgt_conn.cursor()

        logger.info(f"Starting ETL Migration (Sample Limit: {sample_limit if sample_limit else 'None'})...")

        # --- PRE-MIGRATION: Truncate Target Tables ---
        tables_to_truncate = [
            "shelving_job_containers", "non_tray_items", "items", "trays",
            "shelf_positions", "shelves", "sides", "ladders", "aisles", "modules",
            "verification_jobs", "shelving_jobs", "pick_lists", "accession_jobs",
            "owners", "buildings", "media_types", "container_types", "size_class",
            "group_permissions", "user_groups", "groups", "users"
        ]
        
        logger.info("Truncating target tables...")
        for table in tables_to_truncate:
            tgt_cur.execute(f"TRUNCATE TABLE {table} CASCADE")
        tgt_conn.commit()

        # Level 1: System & Metadata (Critical)
        migrate_table(src_conn, tgt_cur, "users", "SELECT * FROM users", is_critical=True)
        migrate_table(src_conn, tgt_cur, "buildings", "SELECT * FROM buildings", is_critical=True)
        migrate_table(src_conn, tgt_cur, "owners", "SELECT * FROM owners", is_critical=True)
        migrate_table(src_conn, tgt_cur, "size_class", "SELECT * FROM size_class", is_critical=True)
        
        # Non-critical Level 1
        migrate_table(src_conn, tgt_cur, "groups", "SELECT * FROM groups")
        migrate_table(src_conn, tgt_cur, "user_groups", "SELECT * FROM user_groups")
        migrate_table(src_conn, tgt_cur, "group_permissions", "SELECT * FROM group_permissions")
        migrate_table(src_conn, tgt_cur, "container_types", "SELECT * FROM container_types")
        migrate_table(src_conn, tgt_cur, "media_types", "SELECT * FROM media_types")

        # Level 2: Physical Hierarchy (Critical for items)
        migrate_table(src_conn, tgt_cur, "modules", "SELECT * FROM modules", is_critical=True)
        
        aisle_query = "SELECT a.id, a.module_id, n.number as aisle_number, a.sort_priority, a.create_dt, a.update_dt FROM aisles a JOIN aisle_numbers n ON a.aisle_number_id = n.id"
        migrate_table(src_conn, tgt_cur, "aisles", aisle_query, is_critical=True)

        migrate_table(src_conn, tgt_cur, "sides", "SELECT * FROM sides", is_critical=True)

        ladder_query = "SELECT l.id, l.side_id, n.number as ladder_number, l.sort_priority, l.create_dt, l.update_dt FROM ladders l JOIN ladder_numbers n ON l.ladder_number_id = n.id"
        migrate_table(src_conn, tgt_cur, "ladders", ladder_query, is_critical=True)

        shelf_query = "SELECT s.id, s.ladder_id, s.shelf_type_id, s.container_type_id, s.owner_id, n.number as shelf_number, s.sort_priority, s.create_dt, s.update_dt FROM shelves s JOIN shelf_numbers n ON s.shelf_number_id = n.id"
        migrate_table(src_conn, tgt_cur, "shelves", shelf_query, is_critical=True)

        pos_query = "SELECT p.id, p.shelf_id, n.number as position_number, p.create_dt, p.update_dt FROM shelf_positions p JOIN shelf_position_numbers n ON p.shelf_position_number_id = n.id"
        migrate_table(src_conn, tgt_cur, "shelf_positions", pos_query, is_critical=True)

        # Level 3: Inventory (Sampling enabled)
        def transform_items(row, cols):
            d = dict(row); d['ils_sync_state'] = 'IN_SYNC'; d['scanned_for_shipping'] = False; d['shipping_bin_id'] = None
            return d
        migrate_table(src_conn, tgt_cur, "trays", "SELECT * FROM trays", limit=sample_limit)
        migrate_table(src_conn, tgt_cur, "items", "SELECT * FROM items", transform_fn=transform_items, limit=sample_limit)
        migrate_table(src_conn, tgt_cur, "non_tray_items", "SELECT * FROM non_tray_items", transform_fn=transform_items, limit=sample_limit)

        # Level 4: Workflows
        def transform_job(row, cols):
            d = dict(row); d['assigned_user_id'] = d.pop('user_id') if 'user_id' in d else None
            return d
        migrate_table(src_conn, tgt_cur, "accession_jobs", "SELECT * FROM accession_jobs", transform_fn=transform_job, limit=sample_limit)
        migrate_table(src_conn, tgt_cur, "pick_lists", "SELECT * FROM pick_lists", transform_fn=transform_job, limit=sample_limit)
        migrate_table(src_conn, tgt_cur, "verification_jobs", "SELECT * FROM verification_jobs", transform_fn=transform_job, limit=sample_limit)
        
        def transform_shelving_job(row, cols):
            d = dict(row); d['assigned_user_id'] = d.pop('user_id') if 'user_id' in d else None
            d.update({'mode': 'Manual', 'allow_unassigned_size': False, 'allow_unassigned_owner': False, 'allow_tiered_owner': False})
            return d
        migrate_table(src_conn, tgt_cur, "shelving_jobs", "SELECT * FROM shelving_jobs", transform_fn=transform_shelving_job, limit=sample_limit)

        # Finalize
        logger.info("Finalizing shelving job relationships...")
        tgt_cur.execute("INSERT INTO shelving_job_containers (shelving_job_id, tray_id, shelved_dt, was_overridden, status, create_dt, update_dt) SELECT shelving_job_id, id, shelved_dt, FALSE, 'Completed', create_dt, update_dt FROM trays WHERE shelving_job_id IS NOT NULL ON CONFLICT DO NOTHING")
        tgt_cur.execute("INSERT INTO shelving_job_containers (shelving_job_id, non_tray_item_id, shelved_dt, was_overridden, status, create_dt, update_dt) SELECT shelving_job_id, id, shelved_dt, FALSE, 'Completed', create_dt, update_dt FROM non_tray_items WHERE shelving_job_id IS NOT NULL ON CONFLICT DO NOTHING")

        tgt_conn.commit()
        logger.info("ETL Migration Completed!")

    except Exception as e:
        logger.error(f"Critical System Error: {e}")
        if tgt_conn: tgt_conn.rollback()
    finally:
        report_path = "migration/migration_errors.json"
        with open(report_path, "w") as f:
            json.dump({"errors": migration_errors, "timestamp": datetime.now().isoformat()}, f, indent=2)
        logger.info(f"Error report written to {report_path}")
        if src_conn: src_conn.close()
        if tgt_conn: tgt_conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FETCH2 High-Volume ETL Migration Tool")
    parser.add_argument("--sample", type=int, help="Limit migration to a small subset of rows for validation (e.g. 100)")
    args = parser.parse_args()
    
    run_migration(sample_limit=args.sample)
