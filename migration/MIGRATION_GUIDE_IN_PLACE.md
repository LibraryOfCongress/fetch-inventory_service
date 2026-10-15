# FETCH2 to LC Migration Guide (Option 2: Clean Slate)

This document outlines the step-by-step process for porting the `FETCH2` backend (`fetch-inventory_service`) back into the original Library of Congress (LC) repository.

This strategy uses the **Option 2 (Autogenerate)** approach to safely force the LC production database to conform perfectly to the new `FETCH2` schema, while simultaneously resolving the `sqlmodel` dependency conflict and the massive 66K code diff.

> [!NOTE]
> **Battle-tested on 2026-05-11.** Every phase of this guide was executed as a live trial run against a local test database. All three issues documented below were discovered and resolved during that trial. The autogenerate step successfully produced a single catch-up migration file.

---

## Prerequisites

- Access to the original LC `fetch-inventory_service` Git repository (local clone)
- Access to the `FETCH2` monorepo's `fetch-inventory_service` folder
- **FETCH2 Docker stack running** (`docker-compose up -d` from the `fetch-fetch-local` directory) — the `inventory-database` container provides the PostgreSQL instance used throughout this guide
- Python 3.12+ with the FETCH2 dependencies installed

---

## Phase 1: Create a Temporary Test Database

Before merging code, you must create a database that simulates the LC production schema state.

> [!WARNING]
> You **must** use a temporary database for this process — not your real development or production database. The autogenerate step will compare the database schema against the FETCH2 Python models to produce the catch-up migration.

1. Start the FETCH2 Docker stack (if not already running):
   ```bash
   cd /path/to/FETCH2/fetch-fetch-local
   docker-compose up -d
   ```
   Wait for the `inventory-database` container to be fully ready before proceeding.

2. Create a temporary test database:
   ```bash
   docker exec inventory-database psql -U postgres -c "CREATE DATABASE lc_baseline_db;"
   ```

---

## Phase 2: The Git "Paste" Merge

We will use Git's built-in rename detection to handle the 128 migration file renames automatically.

> [!TIP]
> **Proven:** During live testing, `git add .` instantly recognized all 128 colon-to-underscore migration renames as `renamed` — not as delete + create. No manual file mapping is required.

1. Open the original LC repository and checkout `main`:
   ```bash
   cd /path/to/lc/fetch-inventory_service
   git checkout main
   ```
2. Create a safe sandbox branch:
   ```bash
   git checkout -b fetch2-migration
   ```
3. Use `rsync` with the `-c` (checksum) flag to guarantee an exact mirror of the FETCH2 code into the LC folder. (Using checksums instead of timestamps ensures files like `pyproject.toml` overwrite correctly even if your local checkout is newer):
   ```bash
   rsync -ac --delete --exclude='.git' /path/to/FETCH2/fetch-inventory_service/ ./
   ```
4. Stage the files to trigger Git's rename detection:
   ```bash
   git add .
   ```
5. Verify the renames were detected:
   ```bash
   git status
   ```
   *You should see ~127 lines that say `renamed:` — 126 are migration files (colons → underscores) and 1 is a typo fix (`app/middlware.py` → `app/middleware.py`). The count is not 128 because the 2 LC post-fork migration files show as `deleted` rather than `renamed` (since FETCH2 doesn't have them). They will be restored in Phase 3.*
6. Commit the raw port:
   ```bash
   git commit -m "Raw FETCH2 code port"
   ```

---

## Phase 3: Clean the Migration Files (CRITICAL)

The FETCH2 rewrite made two changes to the 128 historical migration files:
1. **Renamed** them to replace colons with underscores (for Windows filesystem compatibility).
2. **Rewrote** them to remove `import sqlmodel` and replace SQLModel syntax with pure SQLAlchemy 2.0 syntax.

After the Phase 2 rsync, the `migrations/versions/` folder should only contain the FETCH2 versions of these files (with underscores, without sqlmodel). However, you must verify this and handle three specific issues discovered during testing.

### Step 3a: Verify Colon-Named Files Are Gone

> [!CAUTION]
> The LC `main` branch on GitHub contains **only colon-named** migration files (e.g., `2023_10_15_06:33:28_add_building_table.py`). These files contain `import sqlmodel`, which does not exist in the FETCH2 environment. The `rsync --delete` in Phase 2 should have already replaced them with the FETCH2 underscore versions, but if any colon-named files survive, Alembic will crash with:
> ```
> ModuleNotFoundError: No module named 'sqlmodel'
> ```

Check for any remaining colon-named files:
```bash
ls migrations/versions/*:* 2>/dev/null | wc -l
```
If the count is greater than 0, delete them:
```bash
rm migrations/versions/*:*
```

### Step 3b: Verify the Two Merge-Point Files

> [!CAUTION]
> Two special "merge-point" migration files require extra attention. The LC versions of these files contain `import sqlmodel` AND reference colon-style `down_revision` values. If these are not overwritten by the FETCH2 versions, Alembic will crash with:
> ```
> KeyError: '2025_04_11_17:22:40'
> ```

The two files are:
- `migrations/versions/7765c78711f7_.py`
- `migrations/versions/8d08a42236e8_.py`

Open each file and verify:
1. There is **no** `import sqlmodel` line.
2. The `down_revision` tuple uses **underscores** (e.g., `'2025_04_11_17_22_40'`), not colons.

If either file still has colons or sqlmodel, copy the FETCH2 versions over:
```bash
cp /path/to/FETCH2/fetch-inventory_service/migrations/versions/7765c78711f7_.py migrations/versions/
cp /path/to/FETCH2/fetch-inventory_service/migrations/versions/8d08a42236e8_.py migrations/versions/
```

### Step 3c: Delete New FETCH2 Migrations and Restore the 2 LC Post-Fork Migrations

Your target is **130 total migration files** in the `migrations/versions/` folder:
- **128 historical migrations** (the shared history between LC and FETCH2, renamed from colons to underscores)
- **2 LC post-fork migrations** (added by the LC team after the fork and already deployed to LC production)

Delete everything else — these are the new FETCH2-specific migration files that will be replaced by the single autogenerated catch-up migration.

The new FETCH2 migration files to delete include:
- All files starting with `2025_12_*` through `2026_*` (EXCEPT the 2 LC post-fork files listed below)
- Hash-prefixed files: `6bd613af0dd9_*.py`, `6e36473282a8_*.py`, `70d0a34dcda3_*.py`, `9c973da1bd66_*.py`, `a1b2c3d4e5f6_*.py`, `b2c3d4e5f6g7_*.py`, `bf01acb11b05_*.py`, `f17e1399a6d9_*.py`, `15a1422b2e56_*.py`

```bash
cd migrations/versions
rm -f 2025_12_*.py 2026_*.py 6bd613af0dd9*.py 6e36473282a8*.py \
      70d0a34dcda3*.py 9c973da1bd66*.py a1b2c3d4e5f6*.py \
      b2c3d4e5f6g7*.py bf01acb11b05*.py f17e1399a6d9*.py \
      15a1422b2e56*.py
```

Now restore the **2 LC post-fork migrations** from the LC `main` branch. These have already been applied to the LC production database, so the `alembic_version` table knows about them and they must exist in the folder:
```bash
git checkout main -- \
  "migrations/versions/2026_01_27_10:16:24_uq_verification_jobs_workflow_id.py" \
  "migrations/versions/2026_02_09_12:00:00_add_can_manage_users_permission.py"
```

Rename the files to use underscores:
```bash
mv "migrations/versions/2026_01_27_10:16:24_uq_verification_jobs_workflow_id.py" \
   migrations/versions/2026_01_27_10_16_24_uq_verification_jobs_workflow_id.py

mv "migrations/versions/2026_02_09_12:00:00_add_can_manage_users_permission.py" \
   migrations/versions/2026_02_09_12_00_00_add_can_manage_users_permission.py
```

Now fix the contents of each file. There are **three things** to change:
1. Replace `import sqlmodel` with `import sqlalchemy`
2. Update the `revision` field to use underscores instead of colons
3. Update the `down_revision` field to use underscores instead of colons

> [!CAUTION]
> You must fix both the `revision` and `down_revision` fields in these files. If you fix `down_revision` but forget the `revision` field, the migration chain will break (the second file's `down_revision` won't match the first file's `revision`), and Alembic will crash with a `KeyError`.

Fix **File 1** (`2026_01_27_10_16_24_uq_verification_jobs_workflow_id.py`):
```bash
# Replace sqlmodel with sqlalchemy
sed -i '' 's/import sqlmodel/import sqlalchemy/' \
  migrations/versions/2026_01_27_10_16_24_uq_verification_jobs_workflow_id.py

# Fix the revision ID (colons → underscores)
sed -i '' "s/'2026_01_27_10:16:24'/'2026_01_27_10_16_24'/" \
  migrations/versions/2026_01_27_10_16_24_uq_verification_jobs_workflow_id.py

# Fix the down_revision ID (colons → underscores)
sed -i '' "s/'2025_04_24_18:29:11'/'2025_04_24_18_29_11'/" \
  migrations/versions/2026_01_27_10_16_24_uq_verification_jobs_workflow_id.py
```

Fix **File 2** (`2026_02_09_12_00_00_add_can_manage_users_permission.py`):
```bash
# Fix the revision ID (colons → underscores)
sed -i '' "s/'2026_02_09_12:00:00'/'2026_02_09_12_00_00'/" \
  migrations/versions/2026_02_09_12_00_00_add_can_manage_users_permission.py

# Fix the down_revision ID (colons → underscores)
sed -i '' "s/'2026_01_27_10:16:24'/'2026_01_27_10_16_24'/" \
  migrations/versions/2026_02_09_12_00_00_add_can_manage_users_permission.py
```

Verify both files are clean:
```bash
# Should show NO results (no sqlmodel, no colons in revision fields)
grep -n "sqlmodel" migrations/versions/2026_01_27_*.py migrations/versions/2026_02_09_*.py
grep -n "revision.*:" migrations/versions/2026_01_27_*.py migrations/versions/2026_02_09_*.py
```

Verify the migration chain is intact:
```bash
# File 1: revision and down_revision should both use underscores
grep -n "revision" migrations/versions/2026_01_27_10_16_24_uq_verification_jobs_workflow_id.py
# Expected:
#   revision: str = '2026_01_27_10_16_24'
#   down_revision: Union[str, None] = '2025_04_24_18_29_11'

# File 2: revision and down_revision should both use underscores
grep -n "revision" migrations/versions/2026_02_09_12_00_00_add_can_manage_users_permission.py
# Expected:
#   revision: str = '2026_02_09_12_00_00'
#   down_revision: Union[str, None] = '2026_01_27_10_16_24'
```

Finally, verify you have exactly **130 migration files** and zero files containing sqlmodel:
```bash
ls migrations/versions/*.py | wc -l
# Expected: 130

grep -l "sqlmodel" migrations/versions/*.py | wc -l
# Expected: 0
```

---

## Phase 4: Build the Baseline Database

Run the 130 migrations against your temporary test database to simulate the LC production schema.

```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lc_baseline_db" \
MIGRATION_URL="postgresql://postgres:postgres@localhost:5432/lc_baseline_db" \
poetry run alembic upgrade head
```

The database should migrate through all 130 files. The last migration applied will be one of the 2 LC post-fork migrations. This is now the "head" and it perfectly mirrors the current LC production database schema.

---

## Phase 5: Generate the Catch-Up Migration

> [!IMPORTANT]
> Alembic will refuse to autogenerate if the database is not at `head`. If you see the error `FAILED: Target database is not up to date`, it means Step 3c was not completed — there are still new FETCH2 migration files in the folder that push the head beyond the database's current state. Go back and delete them before running this step.

1. Run the Alembic autogenerate command:
   ```bash
   DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lc_baseline_db" \
   MIGRATION_URL="postgresql://postgres:postgres@localhost:5432/lc_baseline_db" \
   poetry run alembic revision --autogenerate -m "Apply FETCH2 Baseline"
   ```

2. **What happens:** Alembic compares the test database (LC's fork-point state) against the new FETCH2 Python models and generates a single migration file containing all necessary changes.

3. **Review the generated file.** Open it and verify:
   - [ ] New FETCH2 tables are present as `create_table()` calls (e.g., `system_settings`, `shipping_jobs`, `shipping_bins`, `ils_configurations`, `scheduled_exports`, `owner_delivery_locations`)
   - [ ] Column renames are correctly handled to prevent data loss.
   - [ ] Schema type changes look reasonable (e.g., `SmallInteger` → `INTEGER`)
   - [ ] No duplicate columns exist (Alembic will silently skip these)
   - [ ] Enum type changes are handled correctly (Alembic sometimes struggles with enum diffs — manually verify any `ALTER TYPE` commands)

> [!CAUTION]
> Alembic cannot detect column renames automatically. If you renamed a column (e.g., `user_id` → `assigned_user_id`), Alembic will generate a `drop_column('user_id')` and an `add_column('assigned_user_id')`. **This will delete all data in that column.** You must manually replace those two commands in the generated file with a single rename command: `op.alter_column('table_name', 'old_name', new_column_name='new_name')`

4. Test the migration locally:
   ```bash
   DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lc_baseline_db" \
   MIGRATION_URL="postgresql://postgres:postgres@localhost:5432/lc_baseline_db" \
   poetry run alembic upgrade head
   ```

5. Commit and clean up:
   ```bash
   git add .
   git commit -m "Add FETCH2 baseline migration"

   # Drop the temporary database
   docker exec inventory-database psql -U postgres -c "DROP DATABASE lc_baseline_db;"
   ```

---

## Phase 6: Environment Rollout

The generated migration file is now committed to the `fetch2-migration` branch. Deploying it to each environment follows the standard promotion pipeline.

### Deployment Order: Dev → Test → Staging → Production

Each environment has its own PostgreSQL database with its own `alembic_version` table. Run the same three commands in each environment:

```bash
# 1. Pull the new branch
git pull origin fetch2-migration

# 2. Install the new FETCH2 dependencies
poetry install

# 3. Run the migration
poetry run alembic upgrade head
```

### Production Deployment

> [!CAUTION]
> Before running the migration on production, you **MUST** take a full database backup. The catch-up migration contains `drop_table()` and `drop_column()` commands that are **irreversible** without a backup.

```bash
# Step 1: Backup the production database
pg_dump -U postgres -h <db_host> -d <db_name> -F c -f fetch_backup_pre_fetch2.dump

# Step 2: Pull the code
git pull origin fetch2-migration

# Step 3: Install dependencies
poetry install
```

> [!WARNING]
> **Step 4 (CRITICAL): Fix the `alembic_version` table before running migrations.**
>
> In Phase 3, we changed the `revision` IDs of the 2 LC post-fork migration files from colon-style (`2026_02_09_12:00:00`) to underscore-style (`2026_02_09_12_00_00`). The LC production database's `alembic_version` table still stores the **original colon-style hash**. If you run `alembic upgrade head` without fixing this, Alembic will crash with:
> ```
> Can't locate revision identified by '2026_02_09_12:00:00'
> ```
>
> Before running the migration, update the `alembic_version` table to match the new underscore-style revision ID:
> ```sql
> UPDATE alembic_version SET version_num = '2026_02_09_12_00_00'
>   WHERE version_num = '2026_02_09_12:00:00';
> ```
> If the current head is the other LC post-fork migration, use:
> ```sql
> UPDATE alembic_version SET version_num = '2026_01_27_10_16_24'
>   WHERE version_num = '2026_01_27_10:16:24';
> ```
> Verify the update worked:
> ```sql
> SELECT * FROM alembic_version;
> ```

```bash
# Step 5: Run the migration
poetry run alembic upgrade head
```

### Failure Response

| Environment | Action |
|---|---|
| **Dev** | Fix the migration file, re-commit, try again. No impact. |
| **Test** | Same as dev. Drop the test DB and recreate if needed. |
| **Staging** | Pause the rollout. Debug, fix, and re-test from dev. |
| **Production** | Restore from the `pg_dump` backup taken in Step 1. |

### Environment Variables

The only variable that changes per environment is the database connection string. Ensure `DATABASE_URL` and `MIGRATION_URL` are correctly set on each server before running `alembic upgrade head`.

> [!IMPORTANT]
> Because this strategy generates `drop_table()` and `drop_column()` commands for LC features that are not in the FETCH2 models, it **will permanently delete data** residing in those specific LC columns/tables in production. All other existing data (items, locations, users, etc.) will be preserved. Make sure the LC team reviews and explicitly approves the generated migration file before merging.
