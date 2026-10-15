-- =====================================================================
-- migrate_to_squash.sql
--
-- One-shot transform: brings an inventory_service database forward from
-- alembic revision 2025_04_24_18:29:11 (last revision applied to prod
-- as of 2026-05-26) to revision 2026_05_26_squash (the new community
-- squash baseline).
--
-- Reconstitutes the data-preserving steps from the original 158-migration
-- chain (notably the user_id->assigned_user_id rename and the number
-- lookup table backfills) that a naive schema diff would not produce.
--
-- Run with psql, NOT with alembic. Wrapped in a single transaction --
-- any failure rolls the entire DB back. App MUST be scaled to zero
-- before running this (it touches almost every table).
-- =====================================================================

\set ON_ERROR_STOP on

BEGIN;

-- =====================================================================
-- Local session settings (scoped to this transaction):
--   Prod has a default statement_timeout that kills long DDL/UPDATE
--   statements (the 1.16M-row shelf_positions backfill in STEP 2 hits
--   it). SET LOCAL applies only inside this BEGIN/COMMIT, so it doesn't
--   affect any other sessions.
-- =====================================================================
SET LOCAL statement_timeout = 0;
SET LOCAL idle_in_transaction_session_timeout = 0;
SET LOCAL lock_timeout = 0;


-- =====================================================================
-- GUARD: refuse to run against unexpected baseline.
-- =====================================================================
DO $$
BEGIN
    -- Accept either of the two known-good baselines: the older April 2025
    -- prod head, or the Feb 2026 head we observed in the May 26 dump
    -- (which adds uq_verification_jobs_workflow_id on top of the older head).
    IF NOT EXISTS (
        SELECT 1 FROM alembic_version
        WHERE version_num IN ('2025_04_24_18:29:11', '2026_02_09_12:00:00')
    ) THEN
        RAISE EXCEPTION
            'Refusing to migrate: alembic_version % is not one of the '
            'known starting baselines (2025_04_24_18:29:11, 2026_02_09_12:00:00).',
            (SELECT version_num FROM alembic_version);
    END IF;
END $$;


-- =====================================================================
-- STEP 1: RENAME user_id -> assigned_user_id (PRESERVES DATA)
--
-- Migra would emit DROP COLUMN + ADD COLUMN, which would lose ~11k
-- assignment rows across the 4 tables. The original migration
-- (f17e1399a6d9_rename_user_id_to_assigned_user_id.py) was a pure
-- ALTER RENAME, which we replicate here.
--
-- Postgres FK constraints reference columns by internal id, not by name,
-- so the existing fk_*_users_id constraints continue to work after rename.
-- =====================================================================
ALTER TABLE accession_jobs    RENAME COLUMN user_id TO assigned_user_id;
ALTER TABLE shelving_jobs     RENAME COLUMN user_id TO assigned_user_id;
ALTER TABLE verification_jobs RENAME COLUMN user_id TO assigned_user_id;
ALTER TABLE pick_lists        RENAME COLUMN user_id TO assigned_user_id;

-- Swap the old user_id indexes for the new compound-with-status indexes.
DROP INDEX IF EXISTS idx_accession_jobs_user_id;
DROP INDEX IF EXISTS idx_shelving_jobs_user_id;
DROP INDEX IF EXISTS idx_verification_jobs_user_id;
DROP INDEX IF EXISTS idx_pick_lists_user_id;

CREATE INDEX idx_accession_jobs_assigned_user_status    ON accession_jobs    (assigned_user_id, status);
CREATE INDEX idx_shelving_jobs_assigned_user_status     ON shelving_jobs     (assigned_user_id, status);
CREATE INDEX idx_verification_jobs_assigned_user_status ON verification_jobs (assigned_user_id, status);
CREATE INDEX idx_pick_lists_assigned_user_status        ON pick_lists        (assigned_user_id, status);
CREATE INDEX idx_pick_lists_assigned_user_id            ON pick_lists        (assigned_user_id);


-- =====================================================================
-- STEP 1.5: Deduplicate verification_jobs by accession_job_id
--
-- The new schema enforces UNIQUE(accession_job_id) on verification_jobs
-- (per migration a1b2c3d4e5f6_prevent_duplicate_vj). Prod has 13 duplicate
-- groups (~15 extra rows) from the historical race condition where the
-- post-accession background task fired twice. Keep the MAX(id) per
-- accession_job_id (the "winning" run) and re-point any child rows that
-- happen to reference a "loser" row.
-- =====================================================================
WITH ranked AS (
    SELECT id, accession_job_id,
           ROW_NUMBER() OVER (PARTITION BY accession_job_id ORDER BY id DESC) AS rn
    FROM verification_jobs
    WHERE accession_job_id IS NOT NULL
),
losers AS (
    SELECT id FROM ranked WHERE rn > 1
),
winner_of AS (
    -- For each loser, the surviving sibling VJ row.
    SELECT loser.id AS loser_id, winner.id AS winner_id
    FROM ranked loser
    JOIN ranked winner USING (accession_job_id)
    WHERE loser.rn > 1 AND winner.rn = 1
)
UPDATE non_tray_items nti SET verification_job_id = w.winner_id
    FROM winner_of w
    WHERE nti.verification_job_id = w.loser_id;
-- (Same pattern would apply to items/trays; current prod has 0 children for both.)

WITH ranked AS (
    SELECT id, accession_job_id,
           ROW_NUMBER() OVER (PARTITION BY accession_job_id ORDER BY id DESC) AS rn
    FROM verification_jobs
    WHERE accession_job_id IS NOT NULL
)
DELETE FROM verification_jobs WHERE id IN (SELECT id FROM ranked WHERE rn > 1);


-- =====================================================================
-- STEP 1.6: Drop uq_verification_jobs_workflow_id if present
--
-- Prod added this constraint in migration 2026_01_27_uq_verification_jobs_workflow_id.
-- The community canonical schema does NOT have it (only uq_*_accession_job_id),
-- so we drop it here. IF EXISTS so the script also works against DBs at
-- the earlier baseline that never had the constraint.
-- =====================================================================
ALTER TABLE verification_jobs DROP CONSTRAINT IF EXISTS uq_verification_jobs_workflow_id;
DROP INDEX IF EXISTS uq_verification_jobs_workflow_id;


-- =====================================================================
-- STEP 2: BACKFILL number columns from lookup tables (PRESERVES DATA)
--
-- Original migration: c1d2e3f4g5h6_remove_number_lookup_tables.
-- aisle_numbers/ladder_numbers/shelf_numbers/shelf_position_numbers
-- each held a simple {id, number} mapping. We move the number value
-- directly onto the owning table, then drop the lookup tables.
-- =====================================================================

-- 2a. Add new direct columns (nullable initially so the table-wide
--     UPDATE doesn't fail constraint checks during the row scan).
ALTER TABLE aisles          ADD COLUMN aisle_number    SMALLINT;
ALTER TABLE ladders         ADD COLUMN ladder_number   SMALLINT;
ALTER TABLE shelves         ADD COLUMN shelf_number    SMALLINT;
ALTER TABLE shelf_positions ADD COLUMN position_number SMALLINT;

-- 2b. Populate from the lookup tables.
UPDATE aisles
    SET aisle_number = an.number
    FROM aisle_numbers an
    WHERE aisles.aisle_number_id = an.id;

UPDATE ladders
    SET ladder_number = ln.number
    FROM ladder_numbers ln
    WHERE ladders.ladder_number_id = ln.id;

UPDATE shelves
    SET shelf_number = sn.number
    FROM shelf_numbers sn
    WHERE shelves.shelf_number_id = sn.id;

UPDATE shelf_positions
    SET position_number = spn.number
    FROM shelf_position_numbers spn
    WHERE shelf_positions.shelf_position_number_id = spn.id;

-- 2c. NOT NULL once data is in place.
ALTER TABLE aisles          ALTER COLUMN aisle_number    SET NOT NULL;
ALTER TABLE ladders         ALTER COLUMN ladder_number   SET NOT NULL;
ALTER TABLE shelves         ALTER COLUMN shelf_number    SET NOT NULL;
ALTER TABLE shelf_positions ALTER COLUMN position_number SET NOT NULL;

-- 2d. Drop the old unique constraints that referenced the FK columns.
ALTER TABLE aisles          DROP CONSTRAINT IF EXISTS uq_module_aisle_number_id;
ALTER TABLE ladders         DROP CONSTRAINT IF EXISTS uq_side_id_ladder_number_id;
ALTER TABLE shelves         DROP CONSTRAINT IF EXISTS uq_ladder_id_shelf_number_id;
ALTER TABLE shelf_positions DROP CONSTRAINT IF EXISTS uq_shelf_id_shelf_position_number_id;

-- 2e. Drop the FK constraints to the lookup tables.
ALTER TABLE aisles          DROP CONSTRAINT IF EXISTS aisles_aisle_number_id_fkey;
ALTER TABLE ladders         DROP CONSTRAINT IF EXISTS ladders_ladder_number_id_fkey;
ALTER TABLE shelves         DROP CONSTRAINT IF EXISTS shelves_shelf_number_id_fkey;
ALTER TABLE shelf_positions DROP CONSTRAINT IF EXISTS shelf_positions_shelf_position_number_id_fkey;

-- 2f. Drop the old FK columns.
ALTER TABLE aisles          DROP COLUMN aisle_number_id;
ALTER TABLE ladders         DROP COLUMN ladder_number_id;
ALTER TABLE shelves         DROP COLUMN shelf_number_id;
ALTER TABLE shelf_positions DROP COLUMN shelf_position_number_id;

-- 2g. Add the new unique constraints on the direct columns.
ALTER TABLE aisles          ADD CONSTRAINT uq_module_aisle_number    UNIQUE (module_id, aisle_number);
ALTER TABLE ladders         ADD CONSTRAINT uq_side_id_ladder_number  UNIQUE (side_id, ladder_number);
ALTER TABLE shelves         ADD CONSTRAINT uq_ladder_id_shelf_number UNIQUE (ladder_id, shelf_number);
ALTER TABLE shelf_positions ADD CONSTRAINT uq_shelf_id_position_number UNIQUE (shelf_id, position_number);

-- 2h. Drop the lookup tables themselves.
DROP TABLE aisle_numbers;
DROP TABLE ladder_numbers;
DROP TABLE shelf_numbers;
DROP TABLE shelf_position_numbers;


-- =====================================================================
-- STEP 3: Drop physical location strings (INTENTIONAL DATA LOSS)
--
-- Original migration: remove_location (2026_02_27_remove_physical_location_strings).
-- The strings on shelves/shelf_positions are derivable from the relational
-- hierarchy and were removed deliberately.
-- =====================================================================
ALTER TABLE shelves         DROP CONSTRAINT IF EXISTS uq_shelves_internal_loc;
ALTER TABLE shelves         DROP CONSTRAINT IF EXISTS uq_shelves_loc;
ALTER TABLE shelf_positions DROP CONSTRAINT IF EXISTS uq_shelf_positions_internal_location;
ALTER TABLE shelf_positions DROP CONSTRAINT IF EXISTS uq_shelf_positions_location;

ALTER TABLE shelves         DROP COLUMN location;
ALTER TABLE shelves         DROP COLUMN internal_location;
ALTER TABLE shelf_positions DROP COLUMN location;
ALTER TABLE shelf_positions DROP COLUMN internal_location;


-- =====================================================================
-- STEP 4: Audit logging -- DB triggers -> app-level
--
-- Original migration: 2026_02_28_22_45_00_app_level_audit_logging.
-- The DB-level audit triggers are removed; audit_log gets new columns
-- for the app-level event taxonomy. The TRUNCATE is intentional per
-- the original migration (old trigger-based records aren't compatible
-- with the new schema).
-- =====================================================================

-- 4a. Drop trigger function and triggers (function depends on triggers, so order matters).
DROP TRIGGER IF EXISTS audit_log_trigger_accession_jobs    ON accession_jobs;
DROP TRIGGER IF EXISTS audit_log_trigger_items             ON items;
DROP TRIGGER IF EXISTS audit_log_trigger_non_tray_items    ON non_tray_items;
DROP TRIGGER IF EXISTS audit_log_trigger_pick_lists        ON pick_lists;
DROP TRIGGER IF EXISTS audit_log_trigger_refile_jobs       ON refile_jobs;
DROP TRIGGER IF EXISTS audit_log_trigger_shelving_jobs     ON shelving_jobs;
DROP TRIGGER IF EXISTS audit_log_trigger_trays             ON trays;
DROP TRIGGER IF EXISTS audit_log_trigger_verification_jobs ON verification_jobs;
DROP TRIGGER IF EXISTS audit_log_trigger_withdraw_jobs     ON withdraw_jobs;

DROP FUNCTION IF EXISTS audit_trigger();

-- 4b. Truncate old audit data (incompatible with new schema).
TRUNCATE TABLE audit_log;

-- 4c. Relax old NOT NULL constraints (new events may not have these).
ALTER TABLE audit_log ALTER COLUMN table_name     DROP NOT NULL;
ALTER TABLE audit_log ALTER COLUMN record_id      DROP NOT NULL;
ALTER TABLE audit_log ALTER COLUMN operation_type DROP NOT NULL;
ALTER TABLE audit_log ALTER COLUMN updated_by     DROP NOT NULL;
ALTER TABLE audit_log ALTER COLUMN updated_at     DROP NOT NULL;

-- 4d. Add the new event-taxonomy columns.
ALTER TABLE audit_log ADD COLUMN event_type  character varying(100);
ALTER TABLE audit_log ADD COLUMN description character varying(500);
ALTER TABLE audit_log ADD COLUMN entity_type character varying(50);
ALTER TABLE audit_log ADD COLUMN entity_id   character varying(50);
ALTER TABLE audit_log ADD COLUMN job_type    character varying(50);
ALTER TABLE audit_log ADD COLUMN job_id      character varying(50);

CREATE INDEX ix_audit_log_entity     ON audit_log (entity_type, entity_id);
CREATE INDEX ix_audit_log_job        ON audit_log (job_type, job_id);
CREATE INDEX ix_audit_log_event_type ON audit_log (event_type);


-- =====================================================================
-- STEP 5: Enum type updates (existing enums getting values added/changed)
--
-- The pattern: rename old type -> _old, create new with full value set,
-- ALTER each dependent column to cast through text, then DROP the old.
-- =====================================================================

-- Pre-flight: drop defaults that reference the old enums (PG won't let
-- us change column type while a default is set on the old type).
ALTER TABLE batch_uploads  ALTER COLUMN status DROP DEFAULT;
ALTER TABLE refile_jobs    ALTER COLUMN status DROP DEFAULT;
ALTER TABLE requests       ALTER COLUMN status DROP DEFAULT;
ALTER TABLE shelving_jobs  ALTER COLUMN origin DROP DEFAULT;
ALTER TABLE withdraw_jobs  ALTER COLUMN status DROP DEFAULT;

-- Rename each old enum out of the way.
ALTER TYPE accession_status         RENAME TO accession_status__old;
ALTER TYPE batch_upload_status_enum RENAME TO batch_upload_status_enum__old;
ALTER TYPE item_status              RENAME TO item_status__old;
ALTER TYPE non_tray_item_status     RENAME TO non_tray_item_status__old;
ALTER TYPE pick_list_status         RENAME TO pick_list_status__old;
ALTER TYPE refile_job_status_enum   RENAME TO refile_job_status_enum__old;
ALTER TYPE request_status           RENAME TO request_status__old;
ALTER TYPE shelving_origin          RENAME TO shelving_origin__old;
ALTER TYPE shelving_status          RENAME TO shelving_status__old;
ALTER TYPE verification_status      RENAME TO verification_status__old;
ALTER TYPE withdraw_status          RENAME TO withdraw_status__old;

-- Create new versions of each.
CREATE TYPE accession_status         AS ENUM ('Created', 'Assigned', 'Paused', 'Running', 'Cancelled', 'Completed', 'Verified');
CREATE TYPE batch_upload_status_enum AS ENUM ('New', 'Processing', 'Cancelled', 'Failed', 'Uploaded', 'Completed');
CREATE TYPE item_status              AS ENUM ('In', 'Requested', 'Withdrawn', 'Out', 'PickList', 'Accessioned', 'Verified', 'Retrieved');
CREATE TYPE non_tray_item_status     AS ENUM ('In', 'Requested', 'Withdrawn', 'Out', 'PickList', 'Accessioned', 'Verified', 'Retrieved');
CREATE TYPE pick_list_status         AS ENUM ('Created', 'Assigned', 'Paused', 'Running', 'Completed');
CREATE TYPE refile_job_status_enum   AS ENUM ('Created', 'Assigned', 'Paused', 'Running', 'Completed');
CREATE TYPE request_status           AS ENUM ('New', 'PickList', 'Retrieved', 'Completed');
CREATE TYPE shelving_origin          AS ENUM ('Verification', 'Direct', 'List', 'Move');
CREATE TYPE shelving_status          AS ENUM ('Created', 'Assigned', 'Paused', 'Running', 'Cancelled', 'Completed');
CREATE TYPE verification_status      AS ENUM ('Created', 'Assigned', 'Paused', 'Running', 'Cancelled', 'Completed');
CREATE TYPE withdraw_status          AS ENUM ('Created', 'Assigned', 'Paused', 'Running', 'Cancelled', 'Completed', 'Verified');

-- Cast each column to the new type (via text).
ALTER TABLE accession_jobs    ALTER COLUMN status TYPE accession_status         USING status::text::accession_status;
ALTER TABLE batch_uploads     ALTER COLUMN status TYPE batch_upload_status_enum USING status::text::batch_upload_status_enum;
ALTER TABLE items             ALTER COLUMN status TYPE item_status              USING status::text::item_status;
ALTER TABLE non_tray_items    ALTER COLUMN status TYPE non_tray_item_status     USING status::text::non_tray_item_status;
ALTER TABLE pick_lists        ALTER COLUMN status TYPE pick_list_status         USING status::text::pick_list_status;
ALTER TABLE refile_jobs       ALTER COLUMN status TYPE refile_job_status_enum   USING status::text::refile_job_status_enum;
-- requests.status: prod has ~2686 rows with 'InProgress' which was renamed to
-- 'PickList' by migration 2026_02_10_rename_inprogress_to_picklist. Map them
-- explicitly in the USING clause; all other values cast straight through.
ALTER TABLE requests          ALTER COLUMN status TYPE request_status
    USING (CASE status::text
               WHEN 'InProgress' THEN 'PickList'::request_status
               ELSE status::text::request_status
           END);
ALTER TABLE shelving_jobs     ALTER COLUMN origin TYPE shelving_origin          USING origin::text::shelving_origin;
ALTER TABLE shelving_jobs     ALTER COLUMN status TYPE shelving_status          USING status::text::shelving_status;
ALTER TABLE verification_jobs ALTER COLUMN status TYPE verification_status      USING status::text::verification_status;
ALTER TABLE withdraw_jobs     ALTER COLUMN status TYPE withdraw_status          USING status::text::withdraw_status;

-- Restore the defaults on the new types.
ALTER TABLE batch_uploads ALTER COLUMN status SET DEFAULT 'New'::batch_upload_status_enum;
ALTER TABLE refile_jobs   ALTER COLUMN status SET DEFAULT 'Created'::refile_job_status_enum;
ALTER TABLE requests      ALTER COLUMN status SET DEFAULT 'New'::request_status;
ALTER TABLE shelving_jobs ALTER COLUMN origin SET DEFAULT 'Verification'::shelving_origin;
ALTER TABLE withdraw_jobs ALTER COLUMN status SET DEFAULT 'Created'::withdraw_status;

-- Drop the renamed-out old enums.
DROP TYPE accession_status__old;
DROP TYPE batch_upload_status_enum__old;
DROP TYPE item_status__old;
DROP TYPE non_tray_item_status__old;
DROP TYPE pick_list_status__old;
DROP TYPE refile_job_status_enum__old;
DROP TYPE request_status__old;
DROP TYPE shelving_origin__old;
DROP TYPE shelving_status__old;
DROP TYPE verification_status__old;
DROP TYPE withdraw_status__old;


-- =====================================================================
-- STEP 6: Create new enum types
-- =====================================================================
CREATE TYPE adapter_type_enum    AS ENUM ('FOLIO', 'ALMA', 'CUSTOM_MIDDLEWARE');
CREATE TYPE export_frequency     AS ENUM ('daily', 'weekly', 'monthly');
CREATE TYPE export_status        AS ENUM ('pending', 'running', 'completed', 'failed');
CREATE TYPE ils_sync_state_enum  AS ENUM ('IN_SYNC', 'PENDING_SYNC', 'SYNC_ERROR');
CREATE TYPE ils_sync_status_enum AS ENUM ('ACTIVE', 'RESOLVED', 'IGNORED');
CREATE TYPE schedule_type        AS ENUM ('once', 'recurring');
CREATE TYPE shelving_mode        AS ENUM ('Manual', 'PreAssigned', 'MoveTrayItem', 'MoveShelf');
CREATE TYPE shipping_bin_status  AS ENUM ('Open', 'Closed');
CREATE TYPE shipping_status      AS ENUM ('Created', 'Assigned', 'Paused', 'Running', 'Completed');
CREATE TYPE workflow_action_enum AS ENUM ('ACCESSION', 'SHELVING', 'REFILE', 'REQUEST_SYNC', 'PICKLIST');


-- =====================================================================
-- STEP 7: Create new sequences (back the new tables' id columns)
-- =====================================================================
-- The four `AS integer` sequences match canonical's explicit type; the three
-- bigint-id sequences (shelving_job_containers/shipping_bins/shipping_jobs)
-- get integer default which is what canonical also emitted.
CREATE SEQUENCE export_history_id_seq           AS integer;
CREATE SEQUENCE owner_delivery_locations_id_seq AS integer;
CREATE SEQUENCE scheduled_exports_id_seq        AS integer;
CREATE SEQUENCE shelving_job_containers_id_seq;
CREATE SEQUENCE shipping_bins_id_seq;
CREATE SEQUENCE shipping_jobs_id_seq;
CREATE SEQUENCE system_settings_id_seq          AS integer;


-- =====================================================================
-- STEP 8: Create new tables
-- =====================================================================
CREATE TABLE export_history (
    id                  integer NOT NULL DEFAULT nextval('export_history_id_seq'::regclass),
    scheduled_export_id integer,
    filename            character varying(255) NOT NULL,
    file_path           character varying(512) NOT NULL,
    status              export_status,
    error_message       character varying(1000),
    file_size_bytes     bigint,
    expires_at          timestamp with time zone NOT NULL,
    create_dt           timestamp with time zone NOT NULL DEFAULT now(),
    update_dt           timestamp with time zone NOT NULL DEFAULT now()
);

CREATE TABLE ils_configurations (
    id                       uuid NOT NULL,
    name                     character varying(150) NOT NULL,
    adapter_type             adapter_type_enum NOT NULL,
    base_url                 character varying(255) NOT NULL,
    tenant_id                character varying(100) NOT NULL,
    auth_client_id           character varying(255) NOT NULL,
    auth_client_secret       character varying(500) NOT NULL,
    auth_token_url           character varying(255),
    expected_shelved_status  character varying(100) NOT NULL,
    expected_refile_status   character varying(100) NOT NULL,
    is_active                boolean NOT NULL,
    enable_accession_hook    boolean NOT NULL,
    enable_shelving_hook     boolean NOT NULL,
    enable_refile_hook       boolean NOT NULL,
    enable_requests_hook     boolean NOT NULL,
    enable_jit_metadata_hook boolean NOT NULL,
    create_dt                timestamp with time zone NOT NULL,
    update_dt                timestamp with time zone NOT NULL,
    expected_picklist_status character varying(100) NOT NULL DEFAULT 'In Transit'::character varying,
    enable_picklist_hook     boolean NOT NULL DEFAULT false,
    ils_service_point_id     character varying(50)
);

CREATE TABLE ils_sync_errors (
    id                  uuid NOT NULL,
    item_barcode        character varying(100) NOT NULL,
    workflow_action     workflow_action_enum NOT NULL,
    error_message       character varying(1000) NOT NULL,
    status              ils_sync_status_enum NOT NULL,
    resolved_by_user_id integer,
    created_at          timestamp with time zone NOT NULL,
    resolved_at         timestamp with time zone,
    create_dt           timestamp with time zone NOT NULL,
    update_dt           timestamp with time zone NOT NULL
);

CREATE TABLE owner_delivery_locations (
    id                   integer NOT NULL DEFAULT nextval('owner_delivery_locations_id_seq'::regclass),
    owner_id             smallint NOT NULL,
    delivery_location_id integer NOT NULL,
    create_dt            timestamp with time zone NOT NULL DEFAULT now(),
    update_dt            timestamp with time zone NOT NULL DEFAULT now()
);

CREATE TABLE scheduled_exports (
    id              integer NOT NULL DEFAULT nextval('scheduled_exports_id_seq'::regclass),
    name            character varying(255) NOT NULL,
    dataset         character varying(50) NOT NULL,
    filters         jsonb,
    schedule_type   schedule_type,
    frequency       export_frequency,
    retention_days  integer NOT NULL,
    is_active       boolean NOT NULL,
    last_run_at     timestamp with time zone,
    next_run_at     timestamp with time zone,
    create_dt       timestamp with time zone NOT NULL DEFAULT now(),
    update_dt       timestamp with time zone NOT NULL DEFAULT now()
);

CREATE TABLE shelving_job_containers (
    id                         bigint NOT NULL DEFAULT nextval('shelving_job_containers_id_seq'::regclass),
    shelving_job_id            integer NOT NULL,
    tray_id                    integer,
    non_tray_item_id           integer,
    proposed_shelf_position_id integer,
    position_reserved_at       timestamp with time zone,
    actual_shelf_position_id   integer,
    shelved_dt                 timestamp with time zone,
    was_overridden             boolean NOT NULL DEFAULT false,
    override_reason            character varying(255),
    status                     character varying(50) NOT NULL DEFAULT 'Pending'::character varying,
    error_message              character varying(500),
    create_dt                  timestamp with time zone NOT NULL DEFAULT now(),
    update_dt                  timestamp with time zone NOT NULL DEFAULT now(),
    destination_tray_id        bigint,
    item_id                    bigint
);

CREATE TABLE shipping_bins (
    id                   bigint NOT NULL DEFAULT nextval('shipping_bins_id_seq'::regclass),
    shipping_job_id      bigint NOT NULL,
    barcode              character varying(255) NOT NULL,
    delivery_location_id integer,
    status               shipping_bin_status NOT NULL,
    cleared_dt           timestamp with time zone,
    cleared_by_id        integer,
    create_dt            timestamp with time zone NOT NULL,
    update_dt            timestamp with time zone NOT NULL
);

CREATE TABLE shipping_jobs (
    id               bigint NOT NULL DEFAULT nextval('shipping_jobs_id_seq'::regclass),
    status           shipping_status NOT NULL,
    completed_dt     timestamp with time zone,
    run_time         interval,
    last_transition  timestamp with time zone NOT NULL,
    assigned_user_id integer,
    created_by_id    integer,
    create_dt        timestamp with time zone NOT NULL,
    update_dt        timestamp with time zone NOT NULL
);

CREATE TABLE system_settings (
    id          integer NOT NULL DEFAULT nextval('system_settings_id_seq'::regclass),
    key         character varying(100) NOT NULL,
    value       character varying(500) NOT NULL,
    description character varying(500),
    create_dt   timestamp without time zone NOT NULL,
    update_dt   timestamp without time zone NOT NULL
);


-- =====================================================================
-- STEP 9: Additive columns on existing tables
-- =====================================================================
-- Column order matches canonical's pg_dump output (which reflects the order
-- the original migration chain added them in: shipping first, then sync).
ALTER TABLE items          ADD COLUMN shipping_bin_id      bigint;
ALTER TABLE items          ADD COLUMN scanned_for_shipping boolean NOT NULL DEFAULT false;
ALTER TABLE items          ADD COLUMN ils_sync_state       ils_sync_state_enum;

-- non_tray_items has a different add-order from items in canonical:
-- ils_sync_state lands first, then shipping_bin_id, then scanned_for_shipping.
ALTER TABLE non_tray_items ADD COLUMN ils_sync_state       ils_sync_state_enum;
ALTER TABLE non_tray_items ADD COLUMN shipping_bin_id      bigint;
ALTER TABLE non_tray_items ADD COLUMN scanned_for_shipping boolean NOT NULL DEFAULT false;

ALTER TABLE owners         ADD COLUMN ils_configuration_id uuid;

ALTER TABLE requests       ADD COLUMN deleted boolean NOT NULL DEFAULT false;
CREATE INDEX ix_requests_batch_upload_id ON requests (batch_upload_id);

-- Column order matches canonical: mode -> unassigned_size -> unassigned_owner -> tiered_owner.
ALTER TABLE shelving_jobs  ADD COLUMN mode                   shelving_mode;
ALTER TABLE shelving_jobs  ADD COLUMN allow_unassigned_size  boolean NOT NULL DEFAULT false;
ALTER TABLE shelving_jobs  ADD COLUMN allow_unassigned_owner boolean NOT NULL DEFAULT false;
ALTER TABLE shelving_jobs  ADD COLUMN allow_tiered_owner     boolean NOT NULL DEFAULT false;

ALTER TABLE shelves        ALTER COLUMN container_type_id DROP NOT NULL;

ALTER TABLE users          ADD COLUMN default_building_id smallint;


-- =====================================================================
-- STEP 10: modules constraint rebalance
--   The old modules_module_number_key was a uniqueness on (module_number)
--   alone. New schema scopes it to (building_id, module_number).
-- =====================================================================
ALTER TABLE modules DROP CONSTRAINT IF EXISTS modules_module_number_key;
CREATE UNIQUE INDEX uq_modules_building ON modules (building_id, module_number);
ALTER TABLE modules ADD CONSTRAINT uq_modules_building UNIQUE USING INDEX uq_modules_building;


-- =====================================================================
-- STEP 11: Sequence ownership (lets DROP TABLE drop the sequence)
-- =====================================================================
ALTER SEQUENCE export_history_id_seq           OWNED BY export_history.id;
ALTER SEQUENCE owner_delivery_locations_id_seq OWNED BY owner_delivery_locations.id;
ALTER SEQUENCE scheduled_exports_id_seq        OWNED BY scheduled_exports.id;
ALTER SEQUENCE shelving_job_containers_id_seq  OWNED BY shelving_job_containers.id;
ALTER SEQUENCE shipping_bins_id_seq            OWNED BY shipping_bins.id;
ALTER SEQUENCE shipping_jobs_id_seq            OWNED BY shipping_jobs.id;
ALTER SEQUENCE system_settings_id_seq          OWNED BY system_settings.id;

-- Drop the lookup-table sequences (the tables are gone, the sequences may linger).
DROP SEQUENCE IF EXISTS aisle_numbers_id_seq;
DROP SEQUENCE IF EXISTS ladder_numbers_id_seq;
DROP SEQUENCE IF EXISTS shelf_numbers_id_seq;
DROP SEQUENCE IF EXISTS shelf_position_numbers_id_seq;


-- =====================================================================
-- STEP 12: Indexes, primary keys, and unique constraints on new tables
-- =====================================================================

-- Primary keys (created via unique index + ADD CONSTRAINT USING INDEX)
CREATE UNIQUE INDEX export_history_pkey            ON export_history (id);
ALTER TABLE export_history ADD CONSTRAINT export_history_pkey PRIMARY KEY USING INDEX export_history_pkey;

CREATE UNIQUE INDEX ils_configurations_pkey        ON ils_configurations (id);
ALTER TABLE ils_configurations ADD CONSTRAINT ils_configurations_pkey PRIMARY KEY USING INDEX ils_configurations_pkey;

CREATE UNIQUE INDEX ils_sync_errors_pkey           ON ils_sync_errors (id);
ALTER TABLE ils_sync_errors ADD CONSTRAINT ils_sync_errors_pkey PRIMARY KEY USING INDEX ils_sync_errors_pkey;

CREATE UNIQUE INDEX owner_delivery_locations_pkey  ON owner_delivery_locations (id);
ALTER TABLE owner_delivery_locations ADD CONSTRAINT owner_delivery_locations_pkey PRIMARY KEY USING INDEX owner_delivery_locations_pkey;

CREATE UNIQUE INDEX scheduled_exports_pkey         ON scheduled_exports (id);
ALTER TABLE scheduled_exports ADD CONSTRAINT scheduled_exports_pkey PRIMARY KEY USING INDEX scheduled_exports_pkey;

CREATE UNIQUE INDEX shelving_job_containers_pkey   ON shelving_job_containers (id);
ALTER TABLE shelving_job_containers ADD CONSTRAINT shelving_job_containers_pkey PRIMARY KEY USING INDEX shelving_job_containers_pkey;

CREATE UNIQUE INDEX shipping_bins_pkey             ON shipping_bins (id);
ALTER TABLE shipping_bins ADD CONSTRAINT shipping_bins_pkey PRIMARY KEY USING INDEX shipping_bins_pkey;

CREATE UNIQUE INDEX shipping_jobs_pkey             ON shipping_jobs (id);
ALTER TABLE shipping_jobs ADD CONSTRAINT shipping_jobs_pkey PRIMARY KEY USING INDEX shipping_jobs_pkey;

CREATE UNIQUE INDEX system_settings_pkey           ON system_settings (id);
ALTER TABLE system_settings ADD CONSTRAINT system_settings_pkey PRIMARY KEY USING INDEX system_settings_pkey;
CREATE UNIQUE INDEX system_settings_key_key        ON system_settings (key);
ALTER TABLE system_settings ADD CONSTRAINT system_settings_key_key UNIQUE USING INDEX system_settings_key_key;

-- Other unique indexes
CREATE UNIQUE INDEX ix_ils_configurations_name     ON ils_configurations (name);
CREATE UNIQUE INDEX uq_owner_delivery_location     ON owner_delivery_locations (owner_id, delivery_location_id);
ALTER TABLE owner_delivery_locations ADD CONSTRAINT uq_owner_delivery_location UNIQUE USING INDEX uq_owner_delivery_location;
CREATE UNIQUE INDEX uq_verification_jobs_accession_job_id ON verification_jobs (accession_job_id);
ALTER TABLE verification_jobs ADD CONSTRAINT uq_verification_jobs_accession_job_id UNIQUE USING INDEX uq_verification_jobs_accession_job_id;

-- Non-unique secondary indexes
CREATE INDEX ix_ils_sync_errors_item_barcode                    ON ils_sync_errors (item_barcode);
CREATE INDEX ix_owner_delivery_locations_delivery_location_id   ON owner_delivery_locations (delivery_location_id);
CREATE INDEX ix_owner_delivery_locations_owner_id               ON owner_delivery_locations (owner_id);
CREATE INDEX ix_shelving_job_containers_non_tray_item_id        ON shelving_job_containers (non_tray_item_id);
CREATE INDEX ix_shelving_job_containers_proposed_shelf_position_id ON shelving_job_containers (proposed_shelf_position_id);
CREATE INDEX ix_shelving_job_containers_shelving_job_id         ON shelving_job_containers (shelving_job_id);
CREATE INDEX ix_shelving_job_containers_status                  ON shelving_job_containers (status);
CREATE INDEX ix_shelving_job_containers_tray_id                 ON shelving_job_containers (tray_id);
CREATE INDEX ix_shipping_bins_barcode                           ON shipping_bins (barcode);
CREATE INDEX ix_shipping_bins_shipping_job_id                   ON shipping_bins (shipping_job_id);
CREATE INDEX idx_shipping_bin_barcode_uncleared                 ON shipping_bins (barcode, cleared_dt);


-- =====================================================================
-- STEP 13: Foreign keys (defer to end so all tables exist)
-- =====================================================================

ALTER TABLE export_history          ADD CONSTRAINT export_history_scheduled_export_id_fkey FOREIGN KEY (scheduled_export_id) REFERENCES scheduled_exports(id);

ALTER TABLE ils_sync_errors         ADD CONSTRAINT ils_sync_errors_resolved_by_user_id_fkey FOREIGN KEY (resolved_by_user_id) REFERENCES users(id);

ALTER TABLE items                   ADD CONSTRAINT fk_items_shipping_bin FOREIGN KEY (shipping_bin_id) REFERENCES shipping_bins(id);

ALTER TABLE non_tray_items          ADD CONSTRAINT fk_non_tray_items_shipping_bin_id FOREIGN KEY (shipping_bin_id) REFERENCES shipping_bins(id);

ALTER TABLE owner_delivery_locations ADD CONSTRAINT owner_delivery_locations_delivery_location_id_fkey
    FOREIGN KEY (delivery_location_id) REFERENCES delivery_locations(id) ON DELETE CASCADE;
ALTER TABLE owner_delivery_locations ADD CONSTRAINT owner_delivery_locations_owner_id_fkey
    FOREIGN KEY (owner_id) REFERENCES owners(id) ON DELETE CASCADE;

ALTER TABLE owners                  ADD CONSTRAINT fk_owners_ils_configuration_id FOREIGN KEY (ils_configuration_id) REFERENCES ils_configurations(id);

ALTER TABLE shelving_job_containers ADD CONSTRAINT ck_shelving_job_container_tray_xor_non_tray_xor_item
    CHECK ((tray_id IS NOT NULL) OR (non_tray_item_id IS NOT NULL) OR (item_id IS NOT NULL));
ALTER TABLE shelving_job_containers ADD CONSTRAINT shelving_job_containers_actual_shelf_position_id_fkey  FOREIGN KEY (actual_shelf_position_id)   REFERENCES shelf_positions(id);
ALTER TABLE shelving_job_containers ADD CONSTRAINT shelving_job_containers_destination_tray_id_fkey      FOREIGN KEY (destination_tray_id)        REFERENCES trays(id);
ALTER TABLE shelving_job_containers ADD CONSTRAINT shelving_job_containers_item_id_fkey                  FOREIGN KEY (item_id)                    REFERENCES items(id);
ALTER TABLE shelving_job_containers ADD CONSTRAINT shelving_job_containers_non_tray_item_id_fkey         FOREIGN KEY (non_tray_item_id)           REFERENCES non_tray_items(id);
ALTER TABLE shelving_job_containers ADD CONSTRAINT shelving_job_containers_proposed_shelf_position_id_fkey FOREIGN KEY (proposed_shelf_position_id) REFERENCES shelf_positions(id);
ALTER TABLE shelving_job_containers ADD CONSTRAINT shelving_job_containers_shelving_job_id_fkey         FOREIGN KEY (shelving_job_id)            REFERENCES shelving_jobs(id) ON DELETE CASCADE;
ALTER TABLE shelving_job_containers ADD CONSTRAINT shelving_job_containers_tray_id_fkey                FOREIGN KEY (tray_id)                    REFERENCES trays(id);

ALTER TABLE shipping_bins ADD CONSTRAINT shipping_bins_cleared_by_id_fkey        FOREIGN KEY (cleared_by_id)        REFERENCES users(id);
ALTER TABLE shipping_bins ADD CONSTRAINT shipping_bins_delivery_location_id_fkey FOREIGN KEY (delivery_location_id) REFERENCES delivery_locations(id);
ALTER TABLE shipping_bins ADD CONSTRAINT shipping_bins_shipping_job_id_fkey      FOREIGN KEY (shipping_job_id)      REFERENCES shipping_jobs(id);

ALTER TABLE shipping_jobs ADD CONSTRAINT shipping_jobs_assigned_user_id_fkey FOREIGN KEY (assigned_user_id) REFERENCES users(id);
ALTER TABLE shipping_jobs ADD CONSTRAINT shipping_jobs_created_by_id_fkey    FOREIGN KEY (created_by_id)    REFERENCES users(id);

ALTER TABLE users ADD CONSTRAINT users_default_building_id_fkey FOREIGN KEY (default_building_id) REFERENCES buildings(id);


-- =====================================================================
-- STEP 14: Stamp alembic_version to the squash baseline
-- =====================================================================
UPDATE alembic_version SET version_num = '2026_05_26_squash';

COMMIT;

-- end migrate_to_squash.sql
