# FETCH2 ETL Migration Script Manual

This manual provides technical instructions for operating the high-volume data migration script located at `migration/run_etl_migration.py`.

## Overview
The migration script is a specialized Python tool designed to extract data from a legacy Library of Congress (LC) database and load it into a pristine FETCH2 database. It is optimized for high-volume datasets (10M+ rows) and ensures data integrity through topological insertion and fail-fast logic.

## Prerequisites
- **Python 3.9+** with `psycopg2` installed.
- **Network Access:** The script must have line-of-sight to both the SOURCE and TARGET PostgreSQL instances.
- **Environment Variables:**
  - `SOURCE_DB_URL`: Connection string for the legacy database.
  - `TARGET_DB_URL`: Connection string for the new FETCH2 database.

## Command Line Options

### 1. Full Migration
Run the script without arguments to migrate the entire dataset.
```bash
poetry run python migration/run_etl_migration.py
```

### 2. Validation / Sampling Mode
Use the `--sample` flag to migrate only a specific number of rows per table. This is highly recommended for initial testing.
```bash
# Migrate only the first 500 rows of items, trays, and jobs
poetry run python migration/run_etl_migration.py --sample 500
```

---

## Core Features

### 1. High-Volume Streaming (Server-Side Cursors)
The script does **not** load the entire database into RAM. It uses PostgreSQL server-side cursors to stream rows in chunks of 5,000. This allows the migration to run on standard hardware even with 10M+ records.

### 2. Fail-Fast Mechanism (Critical Tables)
To prevent "garbage" error reports caused by missing parent records, the script categorizes tables:
- **CRITICAL:** Infrastructure tables (Buildings, Aisles, Shelves, Users). If these fail, the script **halts immediately**.
- **NON-CRITICAL:** Individual records or jobs. If these fail, the script logs the error and attempts to continue with the next table.

### 3. Topological Insertion
Data is inserted in a specific order (Level 1 → Level 4) to satisfy all foreign key constraints:
1. **System Metadata:** Users, Owners, Buildings.
2. **Physical Hierarchy:** Modules, Aisles, Ladders, Sides, Shelves, Positions.
3. **Inventory:** Trays, Items, Non-Tray Items.
4. **Workflows:** Accession, Pick Lists, Verification, Shelving Jobs.

---

## Error Reporting
Every execution generates a JSON error report at `migration/migration_errors.json`.

### How to Read the Report
The report only contains failed attempts, keeping it concise.
```json
{
  "errors": [
    {
      "table": "items",
      "error": "insert or update on table \"items\" violates foreign key constraint...",
      "critical": false
    }
  ],
  "timestamp": "2026-05-12T14:33:54.383"
}
```
If the `errors` list is empty, the migration was 100% successful.

---

## Recommended Workflow

1. **Deploy Target Schema:** Ensure the FETCH2 database is up and has run all `alembic` migrations.
2. **Run Smoke Test:** 
   ```bash
   poetry run python migration/run_etl_migration.py --sample 100
   ```
3. **Inspect Errors:** Check `migration/migration_errors.json`. Fix any mapping issues in the script.
4. **Run Full Migration:** 
   ```bash
   poetry run python migration/run_etl_migration.py
   ```
5. **Final Validation:** Verify record counts in the FETCH2 database.
