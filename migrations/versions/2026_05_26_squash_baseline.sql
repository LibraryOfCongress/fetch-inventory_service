--
-- PostgreSQL database dump
--

-- Dumped from database version 16.8 (Debian 16.8-1.pgdg120+1)
-- Dumped by pg_dump version 16.8 (Debian 16.8-1.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
-- Original pg_dump line was: SELECT pg_catalog.set_config('search_path', '', false);
-- Stripped because alembic's subsequent INSERT INTO alembic_version is
-- unqualified; an empty search_path would make it fail with UndefinedTable.
-- All CREATE statements below are schema-qualified ("public.foo") so the
-- empty search_path isn't needed for them.
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: accession_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.accession_status AS ENUM (
    'Created',
    'Assigned',
    'Paused',
    'Running',
    'Cancelled',
    'Completed',
    'Verified'
);


--
-- Name: adapter_type_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.adapter_type_enum AS ENUM (
    'FOLIO',
    'ALMA',
    'CUSTOM_MIDDLEWARE'
);


--
-- Name: batch_upload_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.batch_upload_status_enum AS ENUM (
    'New',
    'Processing',
    'Cancelled',
    'Failed',
    'Uploaded',
    'Completed'
);


--
-- Name: change_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.change_type AS ENUM (
    'Added',
    'Removed',
    'BarcodeValueEdit',
    'SizeClassEdit',
    'MediaTypeEdit'
);


--
-- Name: export_frequency; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.export_frequency AS ENUM (
    'daily',
    'weekly',
    'monthly'
);


--
-- Name: export_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.export_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed'
);


--
-- Name: ils_sync_state_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.ils_sync_state_enum AS ENUM (
    'IN_SYNC',
    'PENDING_SYNC',
    'SYNC_ERROR'
);


--
-- Name: ils_sync_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.ils_sync_status_enum AS ENUM (
    'ACTIVE',
    'RESOLVED',
    'IGNORED'
);


--
-- Name: item_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.item_status AS ENUM (
    'In',
    'Requested',
    'Withdrawn',
    'Out',
    'PickList',
    'Accessioned',
    'Verified',
    'Retrieved'
);


--
-- Name: non_tray_item_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.non_tray_item_status AS ENUM (
    'In',
    'Requested',
    'Withdrawn',
    'Out',
    'PickList',
    'Accessioned',
    'Verified',
    'Retrieved'
);


--
-- Name: pick_list_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.pick_list_status AS ENUM (
    'Created',
    'Assigned',
    'Paused',
    'Running',
    'Completed'
);


--
-- Name: refile_job_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.refile_job_status_enum AS ENUM (
    'Created',
    'Assigned',
    'Paused',
    'Running',
    'Completed'
);


--
-- Name: request_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.request_status AS ENUM (
    'New',
    'PickList',
    'Retrieved',
    'Completed'
);


--
-- Name: schedule_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.schedule_type AS ENUM (
    'once',
    'recurring'
);


--
-- Name: shelving_mode; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.shelving_mode AS ENUM (
    'Manual',
    'PreAssigned',
    'MoveTrayItem',
    'MoveShelf'
);


--
-- Name: shelving_origin; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.shelving_origin AS ENUM (
    'Verification',
    'Direct',
    'List',
    'Move'
);


--
-- Name: shelving_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.shelving_status AS ENUM (
    'Created',
    'Assigned',
    'Paused',
    'Running',
    'Cancelled',
    'Completed'
);


--
-- Name: shipping_bin_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.shipping_bin_status AS ENUM (
    'Open',
    'Closed'
);


--
-- Name: shipping_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.shipping_status AS ENUM (
    'Created',
    'Assigned',
    'Paused',
    'Running',
    'Completed'
);


--
-- Name: verification_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.verification_status AS ENUM (
    'Created',
    'Assigned',
    'Paused',
    'Running',
    'Cancelled',
    'Completed'
);


--
-- Name: withdraw_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.withdraw_status AS ENUM (
    'Created',
    'Assigned',
    'Paused',
    'Running',
    'Cancelled',
    'Completed',
    'Verified'
);


--
-- Name: workflow_action_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.workflow_action_enum AS ENUM (
    'ACCESSION',
    'SHELVING',
    'REFILE',
    'REQUEST_SYNC',
    'PICKLIST'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: accession_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.accession_jobs (
    id bigint NOT NULL,
    trayed boolean NOT NULL,
    status public.accession_status,
    assigned_user_id integer,
    run_time interval DEFAULT '00:00:00'::interval NOT NULL,
    last_transition timestamp with time zone NOT NULL,
    owner_id integer,
    container_type_id integer,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    media_type_id integer,
    size_class_id integer,
    workflow_id integer,
    created_by_id integer
);


--
-- Name: accession_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.accession_jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: accession_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.accession_jobs_id_seq OWNED BY public.accession_jobs.id;


--
-- Name: aisles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.aisles (
    id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    module_id integer,
    sort_priority smallint,
    aisle_number smallint NOT NULL
);


--
-- Name: aisles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.aisles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: aisles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.aisles_id_seq OWNED BY public.aisles.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
-- Note: CREATE TABLE IF NOT EXISTS + inline PK so this is idempotent --
-- handles both "alembic pre-created the table" and "fresh DB" cases.
--

CREATE TABLE IF NOT EXISTS public.alembic_version (
    version_num character varying(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    id bigint NOT NULL,
    table_name character varying(50),
    record_id character varying(50),
    operation_type character varying(50),
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_by character varying(50),
    original_values json NOT NULL,
    new_values json NOT NULL,
    last_action character varying(150),
    updated_by_user_id character varying(50),
    event_type character varying(100),
    description character varying(500),
    entity_type character varying(50),
    entity_id character varying(50),
    job_type character varying(50),
    job_id character varying(50)
);


--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- Name: barcode_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.barcode_types (
    id smallint NOT NULL,
    name character varying(25) NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    allowed_pattern character varying(25) NOT NULL
);


--
-- Name: barcode_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.barcode_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: barcode_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.barcode_types_id_seq OWNED BY public.barcode_types.id;


--
-- Name: barcodes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.barcodes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    value character varying(255) NOT NULL,
    type_id integer NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    withdrawn boolean DEFAULT false NOT NULL
);


--
-- Name: batch_uploads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.batch_uploads (
    id bigint NOT NULL,
    user_id integer,
    withdraw_job_id integer,
    file_name character varying NOT NULL,
    file_size bigint,
    file_type character varying,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    status public.batch_upload_status_enum DEFAULT 'New'::public.batch_upload_status_enum
);


--
-- Name: batch_uploads_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.batch_uploads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: batch_uploads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.batch_uploads_id_seq OWNED BY public.batch_uploads.id;


--
-- Name: buildings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.buildings (
    id smallint NOT NULL,
    name character varying(25),
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: buildings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.buildings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: buildings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.buildings_id_seq OWNED BY public.buildings.id;


--
-- Name: container_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.container_types (
    id integer NOT NULL,
    type character varying(25) NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: container_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.container_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: container_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.container_types_id_seq OWNED BY public.container_types.id;


--
-- Name: conveyance_bins; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conveyance_bins (
    id integer NOT NULL,
    barcode_id uuid NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    create_dt timestamp with time zone NOT NULL
);


--
-- Name: conveyance_bins_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conveyance_bins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conveyance_bins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conveyance_bins_id_seq OWNED BY public.conveyance_bins.id;


--
-- Name: delivery_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.delivery_locations (
    id integer NOT NULL,
    name character varying(50),
    address character varying(250) NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: delivery_locations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.delivery_locations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_locations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.delivery_locations_id_seq OWNED BY public.delivery_locations.id;


--
-- Name: export_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.export_history (
    id integer NOT NULL,
    scheduled_export_id integer,
    filename character varying(255) NOT NULL,
    file_path character varying(512) NOT NULL,
    status public.export_status,
    error_message character varying(1000),
    file_size_bytes bigint,
    expires_at timestamp with time zone NOT NULL,
    create_dt timestamp with time zone DEFAULT now() NOT NULL,
    update_dt timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: export_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.export_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: export_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.export_history_id_seq OWNED BY public.export_history.id;


--
-- Name: group_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.group_permissions (
    id smallint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- Name: group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.group_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.group_permissions_id_seq OWNED BY public.group_permissions.id;


--
-- Name: groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.groups (
    id smallint NOT NULL,
    name character varying(75) NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.groups_id_seq OWNED BY public.groups.id;


--
-- Name: ils_configurations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ils_configurations (
    id uuid NOT NULL,
    name character varying(150) NOT NULL,
    adapter_type public.adapter_type_enum NOT NULL,
    base_url character varying(255) NOT NULL,
    tenant_id character varying(100) NOT NULL,
    auth_client_id character varying(255) NOT NULL,
    auth_client_secret character varying(500) NOT NULL,
    auth_token_url character varying(255),
    expected_shelved_status character varying(100) NOT NULL,
    expected_refile_status character varying(100) NOT NULL,
    is_active boolean NOT NULL,
    enable_accession_hook boolean NOT NULL,
    enable_shelving_hook boolean NOT NULL,
    enable_refile_hook boolean NOT NULL,
    enable_requests_hook boolean NOT NULL,
    enable_jit_metadata_hook boolean NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    expected_picklist_status character varying(100) DEFAULT 'In Transit'::character varying NOT NULL,
    enable_picklist_hook boolean DEFAULT false NOT NULL,
    ils_service_point_id character varying(50)
);


--
-- Name: ils_sync_errors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ils_sync_errors (
    id uuid NOT NULL,
    item_barcode character varying(100) NOT NULL,
    workflow_action public.workflow_action_enum NOT NULL,
    error_message character varying(1000) NOT NULL,
    status public.ils_sync_status_enum NOT NULL,
    resolved_by_user_id integer,
    created_at timestamp with time zone NOT NULL,
    resolved_at timestamp with time zone,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: item_withdrawals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.item_withdrawals (
    id bigint NOT NULL,
    item_id integer NOT NULL,
    withdraw_job_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: item_withdrawals_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.item_withdrawals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: item_withdrawals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.item_withdrawals_id_seq OWNED BY public.item_withdrawals.id;


--
-- Name: items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.items (
    id bigint NOT NULL,
    barcode_id uuid,
    tray_id integer,
    title character varying(4000),
    volume character varying(15),
    condition character varying(30),
    arbitrary_data character varying(255),
    subcollection_id integer,
    accession_job_id integer,
    verification_job_id integer,
    accession_dt timestamp with time zone,
    withdrawal_dt timestamp with time zone,
    media_type_id integer,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    owner_id integer,
    container_type_id integer,
    size_class_id integer,
    status public.item_status,
    scanned_for_accession boolean NOT NULL,
    scanned_for_verification boolean NOT NULL,
    scanned_for_refile_queue boolean DEFAULT false NOT NULL,
    scanned_for_refile_queue_dt timestamp with time zone,
    withdrawn_barcode_id uuid,
    withdrawn_location character varying(175),
    withdrawn_internal_location character varying(200),
    withdrawn_loc_bcodes character varying(150),
    scanned_for_refile boolean,
    scanned_for_refile_dt timestamp with time zone,
    shipping_bin_id bigint,
    scanned_for_shipping boolean DEFAULT false NOT NULL,
    ils_sync_state public.ils_sync_state_enum,
    CONSTRAINT ck_items_barcode_xor_withdrawn_barcode CHECK (((barcode_id IS NOT NULL) OR (withdrawn_barcode_id IS NOT NULL)))
);


--
-- Name: items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.items_id_seq OWNED BY public.items.id;


--
-- Name: items_retrieval_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.items_retrieval_events (
    id bigint NOT NULL,
    item_id integer NOT NULL,
    owner_id integer NOT NULL,
    pick_list_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: items_retrieval_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.items_retrieval_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: items_retrieval_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.items_retrieval_events_id_seq OWNED BY public.items_retrieval_events.id;


--
-- Name: ladders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ladders (
    id integer NOT NULL,
    side_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    sort_priority smallint,
    ladder_number smallint NOT NULL
);


--
-- Name: ladders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ladders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ladders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ladders_id_seq OWNED BY public.ladders.id;


--
-- Name: media_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.media_types (
    id smallint NOT NULL,
    name character varying(25) NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    create_dt timestamp with time zone NOT NULL
);


--
-- Name: media_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.media_types_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: media_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.media_types_id_seq OWNED BY public.media_types.id;


--
-- Name: modules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.modules (
    id integer NOT NULL,
    building_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    module_number character varying(50)
);


--
-- Name: modules_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.modules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: modules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.modules_id_seq OWNED BY public.modules.id;


--
-- Name: move_discrepancies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.move_discrepancies (
    id bigint NOT NULL,
    tray_id integer,
    item_id integer,
    non_tray_item_id integer,
    container_type_id integer,
    assigned_user_id integer,
    owner_id integer,
    size_class_id integer,
    original_assigned_location character varying(175),
    current_assigned_location character varying(175),
    error character varying(350),
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    CONSTRAINT ck_s_discrepancy_tray_item_xor_non_tray CHECK (((tray_id IS NOT NULL) OR (non_tray_item_id IS NOT NULL) OR (item_id IS NOT NULL)))
);


--
-- Name: move_discrepancies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.move_discrepancies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: move_discrepancies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.move_discrepancies_id_seq OWNED BY public.move_discrepancies.id;


--
-- Name: non_tray_item_withdrawals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.non_tray_item_withdrawals (
    id bigint NOT NULL,
    non_tray_item_id integer NOT NULL,
    withdraw_job_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: non_tray_item_withdrawals_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.non_tray_item_withdrawals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: non_tray_item_withdrawals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.non_tray_item_withdrawals_id_seq OWNED BY public.non_tray_item_withdrawals.id;


--
-- Name: non_tray_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.non_tray_items (
    id bigint NOT NULL,
    barcode_id uuid,
    owner_id integer,
    container_type_id integer,
    subcollection_id integer,
    accession_job_id integer,
    verification_job_id integer,
    accession_dt timestamp with time zone,
    withdrawal_dt timestamp with time zone,
    media_type_id integer,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    size_class_id integer,
    status public.non_tray_item_status,
    scanned_for_accession boolean NOT NULL,
    scanned_for_verification boolean NOT NULL,
    shelving_job_id integer,
    shelf_position_id integer,
    shelf_position_proposed_id integer,
    scanned_for_shelving boolean DEFAULT false NOT NULL,
    scanned_for_refile_queue boolean DEFAULT false NOT NULL,
    scanned_for_refile_queue_dt timestamp with time zone,
    condition character varying(30),
    withdrawn_barcode_id uuid,
    shelved_dt timestamp with time zone,
    withdrawn_location character varying(175),
    withdrawn_internal_location character varying(200),
    withdrawn_loc_bcodes character varying(150),
    scanned_for_refile boolean,
    scanned_for_refile_dt timestamp with time zone,
    ils_sync_state public.ils_sync_state_enum,
    shipping_bin_id bigint,
    scanned_for_shipping boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_non_tray_items_barcode_xor_withdrawn_barcode CHECK (((barcode_id IS NOT NULL) OR (withdrawn_barcode_id IS NOT NULL)))
);


--
-- Name: non_tray_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.non_tray_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: non_tray_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.non_tray_items_id_seq OWNED BY public.non_tray_items.id;


--
-- Name: non_tray_items_retrieval_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.non_tray_items_retrieval_events (
    id bigint NOT NULL,
    non_tray_item_id integer NOT NULL,
    owner_id integer NOT NULL,
    pick_list_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: non_tray_items_retrieval_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.non_tray_items_retrieval_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: non_tray_items_retrieval_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.non_tray_items_retrieval_events_id_seq OWNED BY public.non_tray_items_retrieval_events.id;


--
-- Name: owner_delivery_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.owner_delivery_locations (
    id integer NOT NULL,
    owner_id smallint NOT NULL,
    delivery_location_id integer NOT NULL,
    create_dt timestamp with time zone DEFAULT now() NOT NULL,
    update_dt timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: owner_delivery_locations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.owner_delivery_locations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: owner_delivery_locations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.owner_delivery_locations_id_seq OWNED BY public.owner_delivery_locations.id;


--
-- Name: owner_tiers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.owner_tiers (
    id smallint NOT NULL,
    level smallint NOT NULL,
    name character varying(50) NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: owner_tiers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.owner_tiers_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: owner_tiers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.owner_tiers_id_seq OWNED BY public.owner_tiers.id;


--
-- Name: owners; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.owners (
    id smallint NOT NULL,
    name character varying(150) NOT NULL,
    owner_tier_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    parent_owner_id integer,
    ils_configuration_id uuid
);


--
-- Name: owners_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.owners_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: owners_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.owners_id_seq OWNED BY public.owners.id;


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permissions (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(255),
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;


--
-- Name: pick_lists; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pick_lists (
    id bigint NOT NULL,
    assigned_user_id integer,
    status public.pick_list_status,
    building_id integer,
    last_transition timestamp with time zone NOT NULL,
    run_time interval NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    created_by_id integer
);


--
-- Name: pick_lists_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pick_lists_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pick_lists_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pick_lists_id_seq OWNED BY public.pick_lists.id;


--
-- Name: priorities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.priorities (
    id integer NOT NULL,
    value character varying(50) NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: priorities_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.priorities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: priorities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.priorities_id_seq OWNED BY public.priorities.id;


--
-- Name: refile_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refile_items (
    item_id integer NOT NULL,
    refile_job_id integer NOT NULL,
    id bigint NOT NULL,
    create_dt timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    update_dt timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: refile_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.refile_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: refile_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.refile_items_id_seq OWNED BY public.refile_items.id;


--
-- Name: refile_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refile_jobs (
    id smallint NOT NULL,
    assigned_user_id integer,
    run_time interval,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    status public.refile_job_status_enum DEFAULT 'Created'::public.refile_job_status_enum,
    last_transition timestamp with time zone NOT NULL,
    created_by_id integer
);


--
-- Name: refile_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.refile_jobs_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: refile_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.refile_jobs_id_seq OWNED BY public.refile_jobs.id;


--
-- Name: refile_non_tray_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refile_non_tray_items (
    non_tray_item_id integer NOT NULL,
    refile_job_id integer NOT NULL,
    id bigint NOT NULL,
    create_dt timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    update_dt timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: refile_non_tray_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.refile_non_tray_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: refile_non_tray_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.refile_non_tray_items_id_seq OWNED BY public.refile_non_tray_items.id;


--
-- Name: request_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.request_types (
    id smallint NOT NULL,
    type character varying(50) NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: request_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.request_types_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: request_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.request_types_id_seq OWNED BY public.request_types.id;


--
-- Name: requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.requests (
    id bigint NOT NULL,
    request_type_id integer,
    item_id integer,
    non_tray_item_id integer,
    delivery_location_id integer,
    priority_id integer,
    external_request_id character varying(255),
    requestor_name character varying(50),
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    building_id integer,
    pick_list_id integer,
    fulfilled boolean DEFAULT false NOT NULL,
    batch_upload_id integer,
    status public.request_status DEFAULT 'New'::public.request_status,
    requested_by_id integer,
    deleted boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_item_xor_non_tray CHECK ((((item_id IS NULL) AND (non_tray_item_id IS NOT NULL)) OR ((non_tray_item_id IS NULL) AND (item_id IS NOT NULL))))
);


--
-- Name: requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.requests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.requests_id_seq OWNED BY public.requests.id;


--
-- Name: scheduled_exports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scheduled_exports (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    dataset character varying(50) NOT NULL,
    filters jsonb,
    schedule_type public.schedule_type,
    frequency public.export_frequency,
    retention_days integer NOT NULL,
    is_active boolean NOT NULL,
    last_run_at timestamp with time zone,
    next_run_at timestamp with time zone,
    create_dt timestamp with time zone DEFAULT now() NOT NULL,
    update_dt timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: scheduled_exports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scheduled_exports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scheduled_exports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scheduled_exports_id_seq OWNED BY public.scheduled_exports.id;


--
-- Name: shelf_positions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shelf_positions (
    id bigint NOT NULL,
    shelf_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    position_number smallint NOT NULL
);


--
-- Name: shelf_positions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shelf_positions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shelf_positions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shelf_positions_id_seq OWNED BY public.shelf_positions.id;


--
-- Name: shelf_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shelf_types (
    id bigint NOT NULL,
    type character varying(50),
    size_class_id integer NOT NULL,
    max_capacity smallint NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: shelf_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shelf_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shelf_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shelf_types_id_seq OWNED BY public.shelf_types.id;


--
-- Name: shelves; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shelves (
    id integer NOT NULL,
    barcode_id uuid,
    height numeric(4,2) NOT NULL,
    width numeric(4,2) NOT NULL,
    depth numeric(4,2) NOT NULL,
    container_type_id integer,
    ladder_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    owner_id integer,
    sort_priority smallint,
    shelf_type_id integer NOT NULL,
    available_space smallint DEFAULT 0 NOT NULL,
    shelf_number smallint NOT NULL
);


--
-- Name: shelves_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shelves_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shelves_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shelves_id_seq OWNED BY public.shelves.id;


--
-- Name: shelving_job_containers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shelving_job_containers (
    id bigint NOT NULL,
    shelving_job_id integer NOT NULL,
    tray_id integer,
    non_tray_item_id integer,
    proposed_shelf_position_id integer,
    position_reserved_at timestamp with time zone,
    actual_shelf_position_id integer,
    shelved_dt timestamp with time zone,
    was_overridden boolean DEFAULT false NOT NULL,
    override_reason character varying(255),
    status character varying(50) DEFAULT 'Pending'::character varying NOT NULL,
    error_message character varying(500),
    create_dt timestamp with time zone DEFAULT now() NOT NULL,
    update_dt timestamp with time zone DEFAULT now() NOT NULL,
    destination_tray_id bigint,
    item_id bigint,
    CONSTRAINT ck_shelving_job_container_tray_xor_non_tray_xor_item CHECK (((tray_id IS NOT NULL) OR (non_tray_item_id IS NOT NULL) OR (item_id IS NOT NULL)))
);


--
-- Name: shelving_job_containers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shelving_job_containers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shelving_job_containers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shelving_job_containers_id_seq OWNED BY public.shelving_job_containers.id;


--
-- Name: shelving_job_discrepancies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shelving_job_discrepancies (
    id bigint NOT NULL,
    shelving_job_id integer,
    tray_id integer,
    non_tray_item_id integer,
    error character varying(350),
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    owner_id integer,
    size_class_id integer,
    assigned_location character varying(175),
    pre_assigned_location character varying(175),
    assigned_user_id integer,
    CONSTRAINT ck_s_discrepancy_tray_xor_non_tray CHECK (((tray_id IS NOT NULL) OR (non_tray_item_id IS NOT NULL)))
);


--
-- Name: shelving_job_discrepancies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shelving_job_discrepancies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shelving_job_discrepancies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shelving_job_discrepancies_id_seq OWNED BY public.shelving_job_discrepancies.id;


--
-- Name: shelving_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shelving_jobs (
    id integer NOT NULL,
    status public.shelving_status,
    assigned_user_id integer,
    run_time interval,
    last_transition timestamp with time zone NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    building_id integer NOT NULL,
    origin public.shelving_origin DEFAULT 'Verification'::public.shelving_origin,
    created_by_id integer,
    mode public.shelving_mode,
    allow_unassigned_size boolean DEFAULT false NOT NULL,
    allow_unassigned_owner boolean DEFAULT false NOT NULL,
    allow_tiered_owner boolean DEFAULT false NOT NULL
);


--
-- Name: shelving_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shelving_jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shelving_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shelving_jobs_id_seq OWNED BY public.shelving_jobs.id;


--
-- Name: shipping_bins; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipping_bins (
    id bigint NOT NULL,
    shipping_job_id bigint NOT NULL,
    barcode character varying(255) NOT NULL,
    delivery_location_id integer,
    status public.shipping_bin_status NOT NULL,
    cleared_dt timestamp with time zone,
    cleared_by_id integer,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: shipping_bins_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shipping_bins_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipping_bins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shipping_bins_id_seq OWNED BY public.shipping_bins.id;


--
-- Name: shipping_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipping_jobs (
    id bigint NOT NULL,
    status public.shipping_status NOT NULL,
    completed_dt timestamp with time zone,
    run_time interval,
    last_transition timestamp with time zone NOT NULL,
    assigned_user_id integer,
    created_by_id integer,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: shipping_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shipping_jobs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipping_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shipping_jobs_id_seq OWNED BY public.shipping_jobs.id;


--
-- Name: side_orientations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.side_orientations (
    id smallint NOT NULL,
    name character varying(5) NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: side_orientations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.side_orientations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: side_orientations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.side_orientations_id_seq OWNED BY public.side_orientations.id;


--
-- Name: sides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sides (
    id integer NOT NULL,
    aisle_id integer NOT NULL,
    side_orientation_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: sides_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sides_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sides_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sides_id_seq OWNED BY public.sides.id;


--
-- Name: size_class; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.size_class (
    id smallint NOT NULL,
    name character varying(50) NOT NULL,
    short_name character varying(11) NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    height numeric(4,2) NOT NULL,
    width numeric(4,2) NOT NULL,
    depth numeric(4,2) NOT NULL
);


--
-- Name: size_class_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.size_class_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: size_class_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.size_class_id_seq OWNED BY public.size_class.id;


--
-- Name: subcollections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subcollections (
    id bigint NOT NULL,
    name character varying(50) NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: subcollections_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.subcollections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: subcollections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.subcollections_id_seq OWNED BY public.subcollections.id;


--
-- Name: system_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_settings (
    id integer NOT NULL,
    key character varying(100) NOT NULL,
    value character varying(500) NOT NULL,
    description character varying(500),
    create_dt timestamp without time zone NOT NULL,
    update_dt timestamp without time zone NOT NULL
);


--
-- Name: system_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.system_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: system_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.system_settings_id_seq OWNED BY public.system_settings.id;


--
-- Name: tray_withdrawals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tray_withdrawals (
    id bigint NOT NULL,
    tray_id integer NOT NULL,
    withdraw_job_id integer NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL
);


--
-- Name: tray_withdrawals_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tray_withdrawals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tray_withdrawals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tray_withdrawals_id_seq OWNED BY public.tray_withdrawals.id;


--
-- Name: trays; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trays (
    id bigint NOT NULL,
    accession_job_id integer,
    verification_job_id integer,
    container_type_id integer,
    barcode_id uuid,
    owner_id integer,
    shelf_position_id integer,
    accession_dt timestamp with time zone,
    shelved_dt timestamp with time zone,
    withdrawal_dt timestamp with time zone,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    media_type_id integer,
    conveyance_bin_id integer,
    size_class_id integer NOT NULL,
    scanned_for_accession boolean NOT NULL,
    collection_accessioned boolean NOT NULL,
    scanned_for_verification boolean NOT NULL,
    collection_verified boolean NOT NULL,
    shelving_job_id integer,
    shelf_position_proposed_id integer,
    scanned_for_shelving boolean DEFAULT false NOT NULL,
    withdrawn_barcode_id uuid,
    withdrawn_location character varying(175),
    withdrawn_internal_location character varying(200),
    withdrawn_loc_bcodes character varying(150),
    CONSTRAINT ck_trays_barcode_xor_withdrawn_barcode CHECK (((barcode_id IS NOT NULL) OR (withdrawn_barcode_id IS NOT NULL)))
);


--
-- Name: trays_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.trays_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: trays_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.trays_id_seq OWNED BY public.trays.id;


--
-- Name: user_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_groups (
    id smallint NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


--
-- Name: user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_groups_id_seq OWNED BY public.user_groups.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    first_name character varying(50) NOT NULL,
    last_name character varying(50) NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    email character varying(100),
    fetch_auth_token character varying(300),
    fetch_auth_expiration timestamp with time zone,
    default_building_id smallint
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: verification_changes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.verification_changes (
    id bigint NOT NULL,
    workflow_id integer,
    tray_barcode_value character varying,
    item_barcode_value character varying,
    completed_by_id integer,
    update_dt timestamp with time zone NOT NULL,
    create_dt timestamp with time zone NOT NULL,
    change_type public.change_type,
    CONSTRAINT ck_item_xor_tray CHECK ((((item_barcode_value IS NOT NULL) AND (tray_barcode_value IS NULL)) OR ((item_barcode_value IS NOT NULL) AND (tray_barcode_value IS NOT NULL))))
);


--
-- Name: verification_changes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.verification_changes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: verification_changes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.verification_changes_id_seq OWNED BY public.verification_changes.id;


--
-- Name: verification_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.verification_jobs (
    id bigint NOT NULL,
    trayed boolean NOT NULL,
    assigned_user_id integer,
    last_transition timestamp with time zone NOT NULL,
    run_time interval DEFAULT '00:00:00'::interval NOT NULL,
    accession_job_id bigint NOT NULL,
    owner_id integer,
    container_type_id integer,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    shelving_job_id integer,
    status public.verification_status,
    media_type_id integer,
    size_class_id integer,
    workflow_id integer,
    created_by_id integer
);


--
-- Name: verification_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.verification_jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: verification_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.verification_jobs_id_seq OWNED BY public.verification_jobs.id;


--
-- Name: withdraw_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.withdraw_jobs (
    id bigint NOT NULL,
    assigned_user_id integer,
    last_transition timestamp with time zone NOT NULL,
    run_time interval NOT NULL,
    pick_list_id integer,
    create_dt timestamp with time zone NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    status public.withdraw_status DEFAULT 'Created'::public.withdraw_status,
    created_by_id integer
);


--
-- Name: withdraw_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.withdraw_jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: withdraw_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.withdraw_jobs_id_seq OWNED BY public.withdraw_jobs.id;


--
-- Name: workflow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow (
    id integer NOT NULL,
    update_dt timestamp with time zone NOT NULL,
    create_dt timestamp with time zone NOT NULL
);


--
-- Name: workflow_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.workflow_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: workflow_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.workflow_id_seq OWNED BY public.workflow.id;


--
-- Name: accession_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accession_jobs ALTER COLUMN id SET DEFAULT nextval('public.accession_jobs_id_seq'::regclass);


--
-- Name: aisles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aisles ALTER COLUMN id SET DEFAULT nextval('public.aisles_id_seq'::regclass);


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- Name: barcode_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.barcode_types ALTER COLUMN id SET DEFAULT nextval('public.barcode_types_id_seq'::regclass);


--
-- Name: batch_uploads id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_uploads ALTER COLUMN id SET DEFAULT nextval('public.batch_uploads_id_seq'::regclass);


--
-- Name: buildings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.buildings ALTER COLUMN id SET DEFAULT nextval('public.buildings_id_seq'::regclass);


--
-- Name: container_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.container_types ALTER COLUMN id SET DEFAULT nextval('public.container_types_id_seq'::regclass);


--
-- Name: conveyance_bins id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conveyance_bins ALTER COLUMN id SET DEFAULT nextval('public.conveyance_bins_id_seq'::regclass);


--
-- Name: delivery_locations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_locations ALTER COLUMN id SET DEFAULT nextval('public.delivery_locations_id_seq'::regclass);


--
-- Name: export_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_history ALTER COLUMN id SET DEFAULT nextval('public.export_history_id_seq'::regclass);


--
-- Name: group_permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_permissions ALTER COLUMN id SET DEFAULT nextval('public.group_permissions_id_seq'::regclass);


--
-- Name: groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups ALTER COLUMN id SET DEFAULT nextval('public.groups_id_seq'::regclass);


--
-- Name: item_withdrawals id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_withdrawals ALTER COLUMN id SET DEFAULT nextval('public.item_withdrawals_id_seq'::regclass);


--
-- Name: items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items ALTER COLUMN id SET DEFAULT nextval('public.items_id_seq'::regclass);


--
-- Name: items_retrieval_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items_retrieval_events ALTER COLUMN id SET DEFAULT nextval('public.items_retrieval_events_id_seq'::regclass);


--
-- Name: ladders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ladders ALTER COLUMN id SET DEFAULT nextval('public.ladders_id_seq'::regclass);


--
-- Name: media_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_types ALTER COLUMN id SET DEFAULT nextval('public.media_types_id_seq'::regclass);


--
-- Name: modules id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modules ALTER COLUMN id SET DEFAULT nextval('public.modules_id_seq'::regclass);


--
-- Name: move_discrepancies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_discrepancies ALTER COLUMN id SET DEFAULT nextval('public.move_discrepancies_id_seq'::regclass);


--
-- Name: non_tray_item_withdrawals id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_item_withdrawals ALTER COLUMN id SET DEFAULT nextval('public.non_tray_item_withdrawals_id_seq'::regclass);


--
-- Name: non_tray_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items ALTER COLUMN id SET DEFAULT nextval('public.non_tray_items_id_seq'::regclass);


--
-- Name: non_tray_items_retrieval_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items_retrieval_events ALTER COLUMN id SET DEFAULT nextval('public.non_tray_items_retrieval_events_id_seq'::regclass);


--
-- Name: owner_delivery_locations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner_delivery_locations ALTER COLUMN id SET DEFAULT nextval('public.owner_delivery_locations_id_seq'::regclass);


--
-- Name: owner_tiers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner_tiers ALTER COLUMN id SET DEFAULT nextval('public.owner_tiers_id_seq'::regclass);


--
-- Name: owners id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owners ALTER COLUMN id SET DEFAULT nextval('public.owners_id_seq'::regclass);


--
-- Name: permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);


--
-- Name: pick_lists id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pick_lists ALTER COLUMN id SET DEFAULT nextval('public.pick_lists_id_seq'::regclass);


--
-- Name: priorities id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.priorities ALTER COLUMN id SET DEFAULT nextval('public.priorities_id_seq'::regclass);


--
-- Name: refile_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_items ALTER COLUMN id SET DEFAULT nextval('public.refile_items_id_seq'::regclass);


--
-- Name: refile_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_jobs ALTER COLUMN id SET DEFAULT nextval('public.refile_jobs_id_seq'::regclass);


--
-- Name: refile_non_tray_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_non_tray_items ALTER COLUMN id SET DEFAULT nextval('public.refile_non_tray_items_id_seq'::regclass);


--
-- Name: request_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.request_types ALTER COLUMN id SET DEFAULT nextval('public.request_types_id_seq'::regclass);


--
-- Name: requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests ALTER COLUMN id SET DEFAULT nextval('public.requests_id_seq'::regclass);


--
-- Name: scheduled_exports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_exports ALTER COLUMN id SET DEFAULT nextval('public.scheduled_exports_id_seq'::regclass);


--
-- Name: shelf_positions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelf_positions ALTER COLUMN id SET DEFAULT nextval('public.shelf_positions_id_seq'::regclass);


--
-- Name: shelf_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelf_types ALTER COLUMN id SET DEFAULT nextval('public.shelf_types_id_seq'::regclass);


--
-- Name: shelves id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelves ALTER COLUMN id SET DEFAULT nextval('public.shelves_id_seq'::regclass);


--
-- Name: shelving_job_containers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_containers ALTER COLUMN id SET DEFAULT nextval('public.shelving_job_containers_id_seq'::regclass);


--
-- Name: shelving_job_discrepancies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_discrepancies ALTER COLUMN id SET DEFAULT nextval('public.shelving_job_discrepancies_id_seq'::regclass);


--
-- Name: shelving_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_jobs ALTER COLUMN id SET DEFAULT nextval('public.shelving_jobs_id_seq'::regclass);


--
-- Name: shipping_bins id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_bins ALTER COLUMN id SET DEFAULT nextval('public.shipping_bins_id_seq'::regclass);


--
-- Name: shipping_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_jobs ALTER COLUMN id SET DEFAULT nextval('public.shipping_jobs_id_seq'::regclass);


--
-- Name: side_orientations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.side_orientations ALTER COLUMN id SET DEFAULT nextval('public.side_orientations_id_seq'::regclass);


--
-- Name: sides id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sides ALTER COLUMN id SET DEFAULT nextval('public.sides_id_seq'::regclass);


--
-- Name: size_class id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.size_class ALTER COLUMN id SET DEFAULT nextval('public.size_class_id_seq'::regclass);


--
-- Name: subcollections id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcollections ALTER COLUMN id SET DEFAULT nextval('public.subcollections_id_seq'::regclass);


--
-- Name: system_settings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings ALTER COLUMN id SET DEFAULT nextval('public.system_settings_id_seq'::regclass);


--
-- Name: tray_withdrawals id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tray_withdrawals ALTER COLUMN id SET DEFAULT nextval('public.tray_withdrawals_id_seq'::regclass);


--
-- Name: trays id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays ALTER COLUMN id SET DEFAULT nextval('public.trays_id_seq'::regclass);


--
-- Name: user_groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_groups ALTER COLUMN id SET DEFAULT nextval('public.user_groups_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: verification_changes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_changes ALTER COLUMN id SET DEFAULT nextval('public.verification_changes_id_seq'::regclass);


--
-- Name: verification_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs ALTER COLUMN id SET DEFAULT nextval('public.verification_jobs_id_seq'::regclass);


--
-- Name: withdraw_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.withdraw_jobs ALTER COLUMN id SET DEFAULT nextval('public.withdraw_jobs_id_seq'::regclass);


--
-- Name: workflow id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow ALTER COLUMN id SET DEFAULT nextval('public.workflow_id_seq'::regclass);


--
-- Name: accession_jobs accession_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accession_jobs
    ADD CONSTRAINT accession_jobs_pkey PRIMARY KEY (id);


--
-- Name: aisles aisles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aisles
    ADD CONSTRAINT aisles_pkey PRIMARY KEY (id);


-- alembic_version_pkc constraint also removed -- alembic creates the table
-- with its own primary key, so re-adding the constraint here would error.


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: barcode_types barcode_types_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.barcode_types
    ADD CONSTRAINT barcode_types_name_key UNIQUE (name);


--
-- Name: barcode_types barcode_types_name_key1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.barcode_types
    ADD CONSTRAINT barcode_types_name_key1 UNIQUE (name);


--
-- Name: barcode_types barcode_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.barcode_types
    ADD CONSTRAINT barcode_types_pkey PRIMARY KEY (id);


--
-- Name: barcodes barcodes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.barcodes
    ADD CONSTRAINT barcodes_pkey PRIMARY KEY (id);


--
-- Name: barcodes barcodes_value_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.barcodes
    ADD CONSTRAINT barcodes_value_key UNIQUE (value);


--
-- Name: barcodes barcodes_value_key1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.barcodes
    ADD CONSTRAINT barcodes_value_key1 UNIQUE (value);


--
-- Name: batch_uploads batch_uploads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_uploads
    ADD CONSTRAINT batch_uploads_pkey PRIMARY KEY (id);


--
-- Name: buildings buildings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.buildings
    ADD CONSTRAINT buildings_pkey PRIMARY KEY (id);


--
-- Name: container_types container_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.container_types
    ADD CONSTRAINT container_types_pkey PRIMARY KEY (id);


--
-- Name: container_types container_types_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.container_types
    ADD CONSTRAINT container_types_type_key UNIQUE (type);


--
-- Name: conveyance_bins conveyance_bins_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conveyance_bins
    ADD CONSTRAINT conveyance_bins_pkey PRIMARY KEY (id);


--
-- Name: delivery_locations delivery_locations_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_locations
    ADD CONSTRAINT delivery_locations_name_key UNIQUE (name);


--
-- Name: delivery_locations delivery_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_locations
    ADD CONSTRAINT delivery_locations_pkey PRIMARY KEY (id);


--
-- Name: export_history export_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_history
    ADD CONSTRAINT export_history_pkey PRIMARY KEY (id);


--
-- Name: group_permissions group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_permissions
    ADD CONSTRAINT group_permissions_pkey PRIMARY KEY (id);


--
-- Name: groups groups_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_name_key UNIQUE (name);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: ils_configurations ils_configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ils_configurations
    ADD CONSTRAINT ils_configurations_pkey PRIMARY KEY (id);


--
-- Name: ils_sync_errors ils_sync_errors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ils_sync_errors
    ADD CONSTRAINT ils_sync_errors_pkey PRIMARY KEY (id);


--
-- Name: item_withdrawals item_withdrawals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_withdrawals
    ADD CONSTRAINT item_withdrawals_pkey PRIMARY KEY (id);


--
-- Name: items item_withdrawn_barcode_id_gen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT item_withdrawn_barcode_id_gen UNIQUE (withdrawn_barcode_id);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


--
-- Name: items_retrieval_events items_retrieval_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items_retrieval_events
    ADD CONSTRAINT items_retrieval_events_pkey PRIMARY KEY (id);


--
-- Name: ladders ladders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ladders
    ADD CONSTRAINT ladders_pkey PRIMARY KEY (id);


--
-- Name: media_types media_types_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_types
    ADD CONSTRAINT media_types_name_key UNIQUE (name);


--
-- Name: media_types media_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_types
    ADD CONSTRAINT media_types_pkey PRIMARY KEY (id);


--
-- Name: modules modules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modules
    ADD CONSTRAINT modules_pkey PRIMARY KEY (id);


--
-- Name: move_discrepancies move_discrepancies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_discrepancies
    ADD CONSTRAINT move_discrepancies_pkey PRIMARY KEY (id);


--
-- Name: non_tray_item_withdrawals non_tray_item_withdrawals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_item_withdrawals
    ADD CONSTRAINT non_tray_item_withdrawals_pkey PRIMARY KEY (id);


--
-- Name: non_tray_items non_tray_item_withdrawn_barcode_id_gen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT non_tray_item_withdrawn_barcode_id_gen UNIQUE (withdrawn_barcode_id);


--
-- Name: non_tray_items non_tray_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT non_tray_items_pkey PRIMARY KEY (id);


--
-- Name: non_tray_items_retrieval_events non_tray_items_retrieval_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items_retrieval_events
    ADD CONSTRAINT non_tray_items_retrieval_events_pkey PRIMARY KEY (id);


--
-- Name: owner_delivery_locations owner_delivery_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner_delivery_locations
    ADD CONSTRAINT owner_delivery_locations_pkey PRIMARY KEY (id);


--
-- Name: owner_tiers owner_tiers_level_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner_tiers
    ADD CONSTRAINT owner_tiers_level_key UNIQUE (level);


--
-- Name: owner_tiers owner_tiers_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner_tiers
    ADD CONSTRAINT owner_tiers_name_key UNIQUE (name);


--
-- Name: owner_tiers owner_tiers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner_tiers
    ADD CONSTRAINT owner_tiers_pkey PRIMARY KEY (id);


--
-- Name: owners owners_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owners
    ADD CONSTRAINT owners_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_name_key UNIQUE (name);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: pick_lists pick_lists_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pick_lists
    ADD CONSTRAINT pick_lists_pkey PRIMARY KEY (id);


--
-- Name: priorities priorities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.priorities
    ADD CONSTRAINT priorities_pkey PRIMARY KEY (id);


--
-- Name: priorities priorities_value_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.priorities
    ADD CONSTRAINT priorities_value_key UNIQUE (value);


--
-- Name: refile_jobs refile_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_jobs
    ADD CONSTRAINT refile_jobs_pkey PRIMARY KEY (id);


--
-- Name: refile_non_tray_items refile_non_tray_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_non_tray_items
    ADD CONSTRAINT refile_non_tray_items_pkey PRIMARY KEY (non_tray_item_id, refile_job_id);


--
-- Name: request_types request_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.request_types
    ADD CONSTRAINT request_types_pkey PRIMARY KEY (id);


--
-- Name: request_types request_types_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.request_types
    ADD CONSTRAINT request_types_type_key UNIQUE (type);


--
-- Name: requests requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_pkey PRIMARY KEY (id);


--
-- Name: scheduled_exports scheduled_exports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_exports
    ADD CONSTRAINT scheduled_exports_pkey PRIMARY KEY (id);


--
-- Name: shelf_positions shelf_positions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelf_positions
    ADD CONSTRAINT shelf_positions_pkey PRIMARY KEY (id);


--
-- Name: shelf_types shelf_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelf_types
    ADD CONSTRAINT shelf_types_pkey PRIMARY KEY (id);


--
-- Name: shelves shelves_barcode_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelves
    ADD CONSTRAINT shelves_barcode_id_key UNIQUE (barcode_id);


--
-- Name: shelves shelves_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelves
    ADD CONSTRAINT shelves_pkey PRIMARY KEY (id);


--
-- Name: shelving_job_containers shelving_job_containers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_containers
    ADD CONSTRAINT shelving_job_containers_pkey PRIMARY KEY (id);


--
-- Name: shelving_job_discrepancies shelving_job_discrepancies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_discrepancies
    ADD CONSTRAINT shelving_job_discrepancies_pkey PRIMARY KEY (id);


--
-- Name: shelving_jobs shelving_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_jobs
    ADD CONSTRAINT shelving_jobs_pkey PRIMARY KEY (id);


--
-- Name: shipping_bins shipping_bins_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_bins
    ADD CONSTRAINT shipping_bins_pkey PRIMARY KEY (id);


--
-- Name: shipping_jobs shipping_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_jobs
    ADD CONSTRAINT shipping_jobs_pkey PRIMARY KEY (id);


--
-- Name: side_orientations side_orientations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.side_orientations
    ADD CONSTRAINT side_orientations_pkey PRIMARY KEY (id);


--
-- Name: sides sides_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sides
    ADD CONSTRAINT sides_pkey PRIMARY KEY (id);


--
-- Name: size_class size_class_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.size_class
    ADD CONSTRAINT size_class_name_key UNIQUE (name);


--
-- Name: size_class size_class_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.size_class
    ADD CONSTRAINT size_class_pkey PRIMARY KEY (id);


--
-- Name: size_class size_class_short_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.size_class
    ADD CONSTRAINT size_class_short_name_key UNIQUE (short_name);


--
-- Name: subcollections subcollections_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcollections
    ADD CONSTRAINT subcollections_name_key UNIQUE (name);


--
-- Name: subcollections subcollections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcollections
    ADD CONSTRAINT subcollections_pkey PRIMARY KEY (id);


--
-- Name: system_settings system_settings_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_key_key UNIQUE (key);


--
-- Name: system_settings system_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_pkey PRIMARY KEY (id);


--
-- Name: tray_withdrawals tray_withdrawals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tray_withdrawals
    ADD CONSTRAINT tray_withdrawals_pkey PRIMARY KEY (id);


--
-- Name: trays tray_withdrawn_barcode_id_gen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT tray_withdrawn_barcode_id_gen UNIQUE (withdrawn_barcode_id);


--
-- Name: trays trays_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT trays_pkey PRIMARY KEY (id);


--
-- Name: item_withdrawals uix_item_withdrawals; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_withdrawals
    ADD CONSTRAINT uix_item_withdrawals UNIQUE (item_id, withdraw_job_id);


--
-- Name: non_tray_item_withdrawals uix_non_tray_item_withdrawals; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_item_withdrawals
    ADD CONSTRAINT uix_non_tray_item_withdrawals UNIQUE (non_tray_item_id, withdraw_job_id);


--
-- Name: tray_withdrawals uix_tray_withdrawals; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tray_withdrawals
    ADD CONSTRAINT uix_tray_withdrawals UNIQUE (tray_id, withdraw_job_id);


--
-- Name: sides uq_aisle_id_side_orientation_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sides
    ADD CONSTRAINT uq_aisle_id_side_orientation_id UNIQUE (aisle_id, side_orientation_id);


--
-- Name: conveyance_bins uq_conveyance_barcode; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conveyance_bins
    ADD CONSTRAINT uq_conveyance_barcode UNIQUE (barcode_id);


--
-- Name: items uq_item_barcode; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT uq_item_barcode UNIQUE (barcode_id);


--
-- Name: refile_items uq_item_id_refile_job_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_items
    ADD CONSTRAINT uq_item_id_refile_job_id UNIQUE (item_id, refile_job_id);


--
-- Name: shelves uq_ladder_id_shelf_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelves
    ADD CONSTRAINT uq_ladder_id_shelf_number UNIQUE (ladder_id, shelf_number);


--
-- Name: aisles uq_module_aisle_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aisles
    ADD CONSTRAINT uq_module_aisle_number UNIQUE (module_id, aisle_number);


--
-- Name: modules uq_modules_building; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modules
    ADD CONSTRAINT uq_modules_building UNIQUE (building_id, module_number);


--
-- Name: owners uq_name_owner_tier_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owners
    ADD CONSTRAINT uq_name_owner_tier_id UNIQUE (name, owner_tier_id);


--
-- Name: refile_non_tray_items uq_non_tray_item_id_refile_job_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_non_tray_items
    ADD CONSTRAINT uq_non_tray_item_id_refile_job_id UNIQUE (non_tray_item_id, refile_job_id);


--
-- Name: non_tray_items uq_non_tray_items_shelf_position_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT uq_non_tray_items_shelf_position_id UNIQUE (shelf_position_id);


--
-- Name: non_tray_items uq_nontray_barcode; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT uq_nontray_barcode UNIQUE (barcode_id);


--
-- Name: owner_delivery_locations uq_owner_delivery_location; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner_delivery_locations
    ADD CONSTRAINT uq_owner_delivery_location UNIQUE (owner_id, delivery_location_id);


--
-- Name: group_permissions uq_permission_id_group_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_permissions
    ADD CONSTRAINT uq_permission_id_group_id UNIQUE (permission_id, group_id);


--
-- Name: shelf_positions uq_shelf_id_position_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelf_positions
    ADD CONSTRAINT uq_shelf_id_position_number UNIQUE (shelf_id, position_number);


--
-- Name: ladders uq_side_id_ladder_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ladders
    ADD CONSTRAINT uq_side_id_ladder_number UNIQUE (side_id, ladder_number);


--
-- Name: side_orientations uq_side_orientation_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.side_orientations
    ADD CONSTRAINT uq_side_orientation_name UNIQUE (name);


--
-- Name: trays uq_tray_barcode; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT uq_tray_barcode UNIQUE (barcode_id);


--
-- Name: trays uq_trays_shelf_position_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT uq_trays_shelf_position_id UNIQUE (shelf_position_id);


--
-- Name: shelf_types uq_type_size_class_shelf_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelf_types
    ADD CONSTRAINT uq_type_size_class_shelf_type UNIQUE (type, size_class_id);


--
-- Name: users uq_user_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_user_email UNIQUE (email);


--
-- Name: user_groups uq_user_id_group_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT uq_user_id_group_id UNIQUE (user_id, group_id);


--
-- Name: verification_jobs uq_verification_jobs_accession_job_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT uq_verification_jobs_accession_job_id UNIQUE (accession_job_id);


--
-- Name: user_groups user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: verification_changes verification_changes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_changes
    ADD CONSTRAINT verification_changes_pkey PRIMARY KEY (id);


--
-- Name: verification_jobs verification_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT verification_jobs_pkey PRIMARY KEY (id);


--
-- Name: withdraw_jobs withdraw_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.withdraw_jobs
    ADD CONSTRAINT withdraw_jobs_pkey PRIMARY KEY (id);


--
-- Name: workflow workflow_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow
    ADD CONSTRAINT workflow_pkey PRIMARY KEY (id);


--
-- Name: audit_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_lookup ON public.audit_log USING btree (record_id, table_name);


--
-- Name: idx_accession_jobs_assigned_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_accession_jobs_assigned_user_status ON public.accession_jobs USING btree (assigned_user_id, status);


--
-- Name: idx_pick_lists_assigned_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pick_lists_assigned_user_id ON public.pick_lists USING btree (assigned_user_id);


--
-- Name: idx_pick_lists_assigned_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pick_lists_assigned_user_status ON public.pick_lists USING btree (assigned_user_id, status);


--
-- Name: idx_shelving_jobs_assigned_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shelving_jobs_assigned_user_status ON public.shelving_jobs USING btree (assigned_user_id, status);


--
-- Name: idx_shipping_bin_barcode_uncleared; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipping_bin_barcode_uncleared ON public.shipping_bins USING btree (barcode, cleared_dt);


--
-- Name: idx_verification_jobs_assigned_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_verification_jobs_assigned_user_status ON public.verification_jobs USING btree (assigned_user_id, status);


--
-- Name: ix_audit_log_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_entity ON public.audit_log USING btree (entity_type, entity_id);


--
-- Name: ix_audit_log_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_event_type ON public.audit_log USING btree (event_type);


--
-- Name: ix_audit_log_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_job ON public.audit_log USING btree (job_type, job_id);


--
-- Name: ix_barcode_types_allowed_pattern; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_barcode_types_allowed_pattern ON public.barcode_types USING btree (allowed_pattern);


--
-- Name: ix_barcodes_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_barcodes_id ON public.barcodes USING btree (id);


--
-- Name: ix_ils_configurations_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_ils_configurations_name ON public.ils_configurations USING btree (name);


--
-- Name: ix_ils_sync_errors_item_barcode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ils_sync_errors_item_barcode ON public.ils_sync_errors USING btree (item_barcode);


--
-- Name: ix_owner_delivery_locations_delivery_location_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_owner_delivery_locations_delivery_location_id ON public.owner_delivery_locations USING btree (delivery_location_id);


--
-- Name: ix_owner_delivery_locations_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_owner_delivery_locations_owner_id ON public.owner_delivery_locations USING btree (owner_id);


--
-- Name: ix_owners_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_owners_name ON public.owners USING btree (name);


--
-- Name: ix_requests_batch_upload_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_requests_batch_upload_id ON public.requests USING btree (batch_upload_id);


--
-- Name: ix_shelf_types_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_shelf_types_type ON public.shelf_types USING btree (type);


--
-- Name: ix_shelving_job_containers_non_tray_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_shelving_job_containers_non_tray_item_id ON public.shelving_job_containers USING btree (non_tray_item_id);


--
-- Name: ix_shelving_job_containers_proposed_shelf_position_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_shelving_job_containers_proposed_shelf_position_id ON public.shelving_job_containers USING btree (proposed_shelf_position_id);


--
-- Name: ix_shelving_job_containers_shelving_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_shelving_job_containers_shelving_job_id ON public.shelving_job_containers USING btree (shelving_job_id);


--
-- Name: ix_shelving_job_containers_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_shelving_job_containers_status ON public.shelving_job_containers USING btree (status);


--
-- Name: ix_shelving_job_containers_tray_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_shelving_job_containers_tray_id ON public.shelving_job_containers USING btree (tray_id);


--
-- Name: ix_shipping_bins_barcode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_shipping_bins_barcode ON public.shipping_bins USING btree (barcode);


--
-- Name: ix_shipping_bins_shipping_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_shipping_bins_shipping_job_id ON public.shipping_bins USING btree (shipping_job_id);


--
-- Name: ix_side_orientations_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_side_orientations_name ON public.side_orientations USING btree (name);


--
-- Name: accession_jobs accession_job_media_type_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accession_jobs
    ADD CONSTRAINT accession_job_media_type_fk FOREIGN KEY (media_type_id) REFERENCES public.media_types(id);


--
-- Name: accession_jobs accession_job_size_class; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accession_jobs
    ADD CONSTRAINT accession_job_size_class FOREIGN KEY (size_class_id) REFERENCES public.size_class(id);


--
-- Name: accession_jobs accession_jobs_container_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accession_jobs
    ADD CONSTRAINT accession_jobs_container_type_id_fkey FOREIGN KEY (container_type_id) REFERENCES public.container_types(id);


--
-- Name: accession_jobs accession_jobs_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accession_jobs
    ADD CONSTRAINT accession_jobs_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.owners(id);


--
-- Name: aisles aisles_module_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aisles
    ADD CONSTRAINT aisles_module_id_fkey FOREIGN KEY (module_id) REFERENCES public.modules(id);


--
-- Name: barcodes barcodes_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.barcodes
    ADD CONSTRAINT barcodes_type_id_fkey FOREIGN KEY (type_id) REFERENCES public.barcode_types(id);


--
-- Name: batch_uploads batch_uploads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_uploads
    ADD CONSTRAINT batch_uploads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: batch_uploads batch_uploads_withdraw_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_uploads
    ADD CONSTRAINT batch_uploads_withdraw_job_id_fkey FOREIGN KEY (withdraw_job_id) REFERENCES public.withdraw_jobs(id);


--
-- Name: conveyance_bins conveyance_bins_barcode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conveyance_bins
    ADD CONSTRAINT conveyance_bins_barcode_id_fkey FOREIGN KEY (barcode_id) REFERENCES public.barcodes(id);


--
-- Name: export_history export_history_scheduled_export_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_history
    ADD CONSTRAINT export_history_scheduled_export_id_fkey FOREIGN KEY (scheduled_export_id) REFERENCES public.scheduled_exports(id);


--
-- Name: accession_jobs fk_acc_job_workflow; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accession_jobs
    ADD CONSTRAINT fk_acc_job_workflow FOREIGN KEY (workflow_id) REFERENCES public.workflow(id);


--
-- Name: accession_jobs fk_accession_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accession_jobs
    ADD CONSTRAINT fk_accession_created_by_user FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: accession_jobs fk_accession_job_users_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accession_jobs
    ADD CONSTRAINT fk_accession_job_users_id FOREIGN KEY (assigned_user_id) REFERENCES public.users(id);


--
-- Name: items fk_items_container_type_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT fk_items_container_type_id FOREIGN KEY (container_type_id) REFERENCES public.container_types(id);


--
-- Name: items fk_items_owner_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT fk_items_owner_id FOREIGN KEY (owner_id) REFERENCES public.owners(id);


--
-- Name: items_retrieval_events fk_items_retrieval_events_item_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items_retrieval_events
    ADD CONSTRAINT fk_items_retrieval_events_item_id FOREIGN KEY (item_id) REFERENCES public.items(id);


--
-- Name: items_retrieval_events fk_items_retrieval_events_owner_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items_retrieval_events
    ADD CONSTRAINT fk_items_retrieval_events_owner_id FOREIGN KEY (owner_id) REFERENCES public.owners(id);


--
-- Name: items_retrieval_events fk_items_retrieval_events_picklist_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items_retrieval_events
    ADD CONSTRAINT fk_items_retrieval_events_picklist_id FOREIGN KEY (pick_list_id) REFERENCES public.pick_lists(id);


--
-- Name: items fk_items_shipping_bin; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT fk_items_shipping_bin FOREIGN KEY (shipping_bin_id) REFERENCES public.shipping_bins(id);


--
-- Name: non_tray_items_retrieval_events fk_non_tray_items_retrieval_events_non_tray_item_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items_retrieval_events
    ADD CONSTRAINT fk_non_tray_items_retrieval_events_non_tray_item_id FOREIGN KEY (non_tray_item_id) REFERENCES public.non_tray_items(id);


--
-- Name: non_tray_items_retrieval_events fk_non_tray_items_retrieval_events_owner_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items_retrieval_events
    ADD CONSTRAINT fk_non_tray_items_retrieval_events_owner_id FOREIGN KEY (owner_id) REFERENCES public.owners(id);


--
-- Name: non_tray_items_retrieval_events fk_non_tray_items_retrieval_events_picklist_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items_retrieval_events
    ADD CONSTRAINT fk_non_tray_items_retrieval_events_picklist_id FOREIGN KEY (pick_list_id) REFERENCES public.pick_lists(id);


--
-- Name: non_tray_items fk_non_tray_items_shipping_bin_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT fk_non_tray_items_shipping_bin_id FOREIGN KEY (shipping_bin_id) REFERENCES public.shipping_bins(id);


--
-- Name: non_tray_items fk_nontray_shelf_position_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT fk_nontray_shelf_position_id FOREIGN KEY (shelf_position_id) REFERENCES public.shelf_positions(id);


--
-- Name: non_tray_items fk_nontray_shelving_job_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT fk_nontray_shelving_job_id FOREIGN KEY (shelving_job_id) REFERENCES public.shelving_jobs(id);


--
-- Name: owners fk_owners_ils_configuration_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owners
    ADD CONSTRAINT fk_owners_ils_configuration_id FOREIGN KEY (ils_configuration_id) REFERENCES public.ils_configurations(id);


--
-- Name: owners fk_owners_parent_owner_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owners
    ADD CONSTRAINT fk_owners_parent_owner_id FOREIGN KEY (parent_owner_id) REFERENCES public.owners(id);


--
-- Name: pick_lists fk_pl_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pick_lists
    ADD CONSTRAINT fk_pl_created_by_user FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: refile_jobs fk_refile_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_jobs
    ADD CONSTRAINT fk_refile_created_by_user FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: requests fk_requests_building; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT fk_requests_building FOREIGN KEY (building_id) REFERENCES public.buildings(id);


--
-- Name: shelving_job_discrepancies fk_s_d_owner_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_discrepancies
    ADD CONSTRAINT fk_s_d_owner_id FOREIGN KEY (owner_id) REFERENCES public.owners(id);


--
-- Name: shelving_job_discrepancies fk_s_d_size_class; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_discrepancies
    ADD CONSTRAINT fk_s_d_size_class FOREIGN KEY (size_class_id) REFERENCES public.size_class(id);


--
-- Name: shelving_job_discrepancies fk_s_j_d_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_discrepancies
    ADD CONSTRAINT fk_s_j_d_user_id FOREIGN KEY (assigned_user_id) REFERENCES public.users(id);


--
-- Name: shelving_jobs fk_shelving_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_jobs
    ADD CONSTRAINT fk_shelving_created_by_user FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: shelving_jobs fk_shelving_job_users_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_jobs
    ADD CONSTRAINT fk_shelving_job_users_id FOREIGN KEY (assigned_user_id) REFERENCES public.users(id);


--
-- Name: shelving_jobs fk_shelvingjob_building_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_jobs
    ADD CONSTRAINT fk_shelvingjob_building_id FOREIGN KEY (building_id) REFERENCES public.buildings(id);


--
-- Name: trays fk_tray_shelving_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT fk_tray_shelving_job FOREIGN KEY (shelving_job_id) REFERENCES public.shelving_jobs(id);


--
-- Name: verification_jobs fk_ver_job_workflow; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT fk_ver_job_workflow FOREIGN KEY (workflow_id) REFERENCES public.workflow(id);


--
-- Name: verification_changes fk_verification_changes_completed_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_changes
    ADD CONSTRAINT fk_verification_changes_completed_by_id_users FOREIGN KEY (completed_by_id) REFERENCES public.users(id);


--
-- Name: verification_changes fk_verification_changes_workflow_id_verification_jobs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_changes
    ADD CONSTRAINT fk_verification_changes_workflow_id_verification_jobs FOREIGN KEY (workflow_id) REFERENCES public.workflow(id);


--
-- Name: verification_jobs fk_verification_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT fk_verification_created_by_user FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: verification_jobs fk_verification_job_users_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT fk_verification_job_users_id FOREIGN KEY (assigned_user_id) REFERENCES public.users(id);


--
-- Name: verification_jobs fk_verification_media_type; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT fk_verification_media_type FOREIGN KEY (media_type_id) REFERENCES public.media_types(id);


--
-- Name: verification_jobs fk_verification_shelving_jobs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT fk_verification_shelving_jobs FOREIGN KEY (shelving_job_id) REFERENCES public.shelving_jobs(id);


--
-- Name: verification_jobs fk_verification_size_class; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT fk_verification_size_class FOREIGN KEY (size_class_id) REFERENCES public.size_class(id);


--
-- Name: withdraw_jobs fk_withdraw_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.withdraw_jobs
    ADD CONSTRAINT fk_withdraw_created_by_user FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: group_permissions group_permissions_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_permissions
    ADD CONSTRAINT group_permissions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);


--
-- Name: group_permissions group_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_permissions
    ADD CONSTRAINT group_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id);


--
-- Name: ils_sync_errors ils_sync_errors_resolved_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ils_sync_errors
    ADD CONSTRAINT ils_sync_errors_resolved_by_user_id_fkey FOREIGN KEY (resolved_by_user_id) REFERENCES public.users(id);


--
-- Name: item_withdrawals item_withdrawals_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_withdrawals
    ADD CONSTRAINT item_withdrawals_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id);


--
-- Name: item_withdrawals item_withdrawals_withdraw_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_withdrawals
    ADD CONSTRAINT item_withdrawals_withdraw_job_id_fkey FOREIGN KEY (withdraw_job_id) REFERENCES public.withdraw_jobs(id);


--
-- Name: items items_accession_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_accession_job_id_fkey FOREIGN KEY (accession_job_id) REFERENCES public.accession_jobs(id);


--
-- Name: items items_barcode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_barcode_id_fkey FOREIGN KEY (barcode_id) REFERENCES public.barcodes(id);


--
-- Name: items items_media_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_media_type_id_fkey FOREIGN KEY (media_type_id) REFERENCES public.media_types(id);


--
-- Name: items items_size_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_size_class_id_fkey FOREIGN KEY (size_class_id) REFERENCES public.size_class(id);


--
-- Name: items items_subcollection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_subcollection_id_fkey FOREIGN KEY (subcollection_id) REFERENCES public.subcollections(id);


--
-- Name: items items_tray_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_tray_id_fkey FOREIGN KEY (tray_id) REFERENCES public.trays(id);


--
-- Name: items items_verification_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_verification_job_id_fkey FOREIGN KEY (verification_job_id) REFERENCES public.verification_jobs(id);


--
-- Name: ladders ladders_side_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ladders
    ADD CONSTRAINT ladders_side_id_fkey FOREIGN KEY (side_id) REFERENCES public.sides(id);


--
-- Name: modules modules_building_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modules
    ADD CONSTRAINT modules_building_id_fkey FOREIGN KEY (building_id) REFERENCES public.buildings(id);


--
-- Name: move_discrepancies move_discrepancies_assigned_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_discrepancies
    ADD CONSTRAINT move_discrepancies_assigned_user_id_fkey FOREIGN KEY (assigned_user_id) REFERENCES public.users(id);


--
-- Name: move_discrepancies move_discrepancies_container_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_discrepancies
    ADD CONSTRAINT move_discrepancies_container_type_id_fkey FOREIGN KEY (container_type_id) REFERENCES public.container_types(id);


--
-- Name: move_discrepancies move_discrepancies_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_discrepancies
    ADD CONSTRAINT move_discrepancies_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id);


--
-- Name: move_discrepancies move_discrepancies_non_tray_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_discrepancies
    ADD CONSTRAINT move_discrepancies_non_tray_item_id_fkey FOREIGN KEY (non_tray_item_id) REFERENCES public.non_tray_items(id);


--
-- Name: move_discrepancies move_discrepancies_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_discrepancies
    ADD CONSTRAINT move_discrepancies_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.owners(id);


--
-- Name: move_discrepancies move_discrepancies_size_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_discrepancies
    ADD CONSTRAINT move_discrepancies_size_class_id_fkey FOREIGN KEY (size_class_id) REFERENCES public.size_class(id);


--
-- Name: move_discrepancies move_discrepancies_tray_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_discrepancies
    ADD CONSTRAINT move_discrepancies_tray_id_fkey FOREIGN KEY (tray_id) REFERENCES public.trays(id);


--
-- Name: non_tray_item_withdrawals non_tray_item_withdrawals_non_tray_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_item_withdrawals
    ADD CONSTRAINT non_tray_item_withdrawals_non_tray_item_id_fkey FOREIGN KEY (non_tray_item_id) REFERENCES public.non_tray_items(id);


--
-- Name: non_tray_item_withdrawals non_tray_item_withdrawals_withdraw_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_item_withdrawals
    ADD CONSTRAINT non_tray_item_withdrawals_withdraw_job_id_fkey FOREIGN KEY (withdraw_job_id) REFERENCES public.withdraw_jobs(id);


--
-- Name: non_tray_items non_tray_items_accession_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT non_tray_items_accession_job_id_fkey FOREIGN KEY (accession_job_id) REFERENCES public.accession_jobs(id);


--
-- Name: non_tray_items non_tray_items_barcode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT non_tray_items_barcode_id_fkey FOREIGN KEY (barcode_id) REFERENCES public.barcodes(id);


--
-- Name: non_tray_items non_tray_items_container_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT non_tray_items_container_type_id_fkey FOREIGN KEY (container_type_id) REFERENCES public.container_types(id);


--
-- Name: non_tray_items non_tray_items_media_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT non_tray_items_media_type_id_fkey FOREIGN KEY (media_type_id) REFERENCES public.media_types(id);


--
-- Name: non_tray_items non_tray_items_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT non_tray_items_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.owners(id);


--
-- Name: non_tray_items non_tray_items_size_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT non_tray_items_size_class_id_fkey FOREIGN KEY (size_class_id) REFERENCES public.size_class(id);


--
-- Name: non_tray_items non_tray_items_subcollection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT non_tray_items_subcollection_id_fkey FOREIGN KEY (subcollection_id) REFERENCES public.subcollections(id);


--
-- Name: non_tray_items non_tray_items_verification_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT non_tray_items_verification_job_id_fkey FOREIGN KEY (verification_job_id) REFERENCES public.verification_jobs(id);


--
-- Name: owner_delivery_locations owner_delivery_locations_delivery_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner_delivery_locations
    ADD CONSTRAINT owner_delivery_locations_delivery_location_id_fkey FOREIGN KEY (delivery_location_id) REFERENCES public.delivery_locations(id) ON DELETE CASCADE;


--
-- Name: owner_delivery_locations owner_delivery_locations_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner_delivery_locations
    ADD CONSTRAINT owner_delivery_locations_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.owners(id) ON DELETE CASCADE;


--
-- Name: owners owners_owner_tier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owners
    ADD CONSTRAINT owners_owner_tier_id_fkey FOREIGN KEY (owner_tier_id) REFERENCES public.owner_tiers(id);


--
-- Name: pick_lists pick_lists_building_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pick_lists
    ADD CONSTRAINT pick_lists_building_id_fkey FOREIGN KEY (building_id) REFERENCES public.buildings(id);


--
-- Name: pick_lists pick_lists_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pick_lists
    ADD CONSTRAINT pick_lists_user_id_fkey FOREIGN KEY (assigned_user_id) REFERENCES public.users(id);


--
-- Name: refile_items refile_items_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_items
    ADD CONSTRAINT refile_items_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id);


--
-- Name: refile_items refile_items_refile_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_items
    ADD CONSTRAINT refile_items_refile_job_id_fkey FOREIGN KEY (refile_job_id) REFERENCES public.refile_jobs(id);


--
-- Name: refile_jobs refile_jobs_assigned_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_jobs
    ADD CONSTRAINT refile_jobs_assigned_user_id_fkey FOREIGN KEY (assigned_user_id) REFERENCES public.users(id);


--
-- Name: refile_non_tray_items refile_non_tray_items_non_tray_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_non_tray_items
    ADD CONSTRAINT refile_non_tray_items_non_tray_item_id_fkey FOREIGN KEY (non_tray_item_id) REFERENCES public.non_tray_items(id);


--
-- Name: refile_non_tray_items refile_non_tray_items_refile_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refile_non_tray_items
    ADD CONSTRAINT refile_non_tray_items_refile_job_id_fkey FOREIGN KEY (refile_job_id) REFERENCES public.refile_jobs(id);


--
-- Name: requests requested_by_id_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requested_by_id_fk FOREIGN KEY (requested_by_id) REFERENCES public.users(id);


--
-- Name: requests requests_batch_upload_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_batch_upload_id_fkey FOREIGN KEY (batch_upload_id) REFERENCES public.batch_uploads(id);


--
-- Name: requests requests_delivery_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_delivery_location_id_fkey FOREIGN KEY (delivery_location_id) REFERENCES public.delivery_locations(id);


--
-- Name: requests requests_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id);


--
-- Name: requests requests_non_tray_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_non_tray_item_id_fkey FOREIGN KEY (non_tray_item_id) REFERENCES public.non_tray_items(id);


--
-- Name: requests requests_pick_list_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_pick_list_id_fkey FOREIGN KEY (pick_list_id) REFERENCES public.pick_lists(id);


--
-- Name: requests requests_priority_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_priority_id_fkey FOREIGN KEY (priority_id) REFERENCES public.priorities(id);


--
-- Name: requests requests_request_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_request_type_id_fkey FOREIGN KEY (request_type_id) REFERENCES public.request_types(id);


--
-- Name: shelf_positions shelf_positions_shelf_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelf_positions
    ADD CONSTRAINT shelf_positions_shelf_id_fkey FOREIGN KEY (shelf_id) REFERENCES public.shelves(id);


--
-- Name: shelves shelf_types_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelves
    ADD CONSTRAINT shelf_types_id_fkey FOREIGN KEY (shelf_type_id) REFERENCES public.shelf_types(id);


--
-- Name: shelf_types shelf_types_size_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelf_types
    ADD CONSTRAINT shelf_types_size_class_id_fkey FOREIGN KEY (size_class_id) REFERENCES public.size_class(id);


--
-- Name: shelves shelves_barcode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelves
    ADD CONSTRAINT shelves_barcode_id_fkey FOREIGN KEY (barcode_id) REFERENCES public.barcodes(id);


--
-- Name: shelves shelves_container_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelves
    ADD CONSTRAINT shelves_container_type_id_fkey FOREIGN KEY (container_type_id) REFERENCES public.container_types(id);


--
-- Name: shelves shelves_ladder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelves
    ADD CONSTRAINT shelves_ladder_id_fkey FOREIGN KEY (ladder_id) REFERENCES public.ladders(id);


--
-- Name: shelves shelves_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelves
    ADD CONSTRAINT shelves_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.owners(id);


--
-- Name: shelving_job_containers shelving_job_containers_actual_shelf_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_containers
    ADD CONSTRAINT shelving_job_containers_actual_shelf_position_id_fkey FOREIGN KEY (actual_shelf_position_id) REFERENCES public.shelf_positions(id);


--
-- Name: shelving_job_containers shelving_job_containers_destination_tray_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_containers
    ADD CONSTRAINT shelving_job_containers_destination_tray_id_fkey FOREIGN KEY (destination_tray_id) REFERENCES public.trays(id);


--
-- Name: shelving_job_containers shelving_job_containers_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_containers
    ADD CONSTRAINT shelving_job_containers_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id);


--
-- Name: shelving_job_containers shelving_job_containers_non_tray_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_containers
    ADD CONSTRAINT shelving_job_containers_non_tray_item_id_fkey FOREIGN KEY (non_tray_item_id) REFERENCES public.non_tray_items(id);


--
-- Name: shelving_job_containers shelving_job_containers_proposed_shelf_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_containers
    ADD CONSTRAINT shelving_job_containers_proposed_shelf_position_id_fkey FOREIGN KEY (proposed_shelf_position_id) REFERENCES public.shelf_positions(id);


--
-- Name: shelving_job_containers shelving_job_containers_shelving_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_containers
    ADD CONSTRAINT shelving_job_containers_shelving_job_id_fkey FOREIGN KEY (shelving_job_id) REFERENCES public.shelving_jobs(id) ON DELETE CASCADE;


--
-- Name: shelving_job_containers shelving_job_containers_tray_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_containers
    ADD CONSTRAINT shelving_job_containers_tray_id_fkey FOREIGN KEY (tray_id) REFERENCES public.trays(id);


--
-- Name: shelving_job_discrepancies shelving_job_discrepancies_non_tray_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_discrepancies
    ADD CONSTRAINT shelving_job_discrepancies_non_tray_item_id_fkey FOREIGN KEY (non_tray_item_id) REFERENCES public.non_tray_items(id);


--
-- Name: shelving_job_discrepancies shelving_job_discrepancies_shelving_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_discrepancies
    ADD CONSTRAINT shelving_job_discrepancies_shelving_job_id_fkey FOREIGN KEY (shelving_job_id) REFERENCES public.shelving_jobs(id);


--
-- Name: shelving_job_discrepancies shelving_job_discrepancies_tray_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shelving_job_discrepancies
    ADD CONSTRAINT shelving_job_discrepancies_tray_id_fkey FOREIGN KEY (tray_id) REFERENCES public.trays(id);


--
-- Name: shipping_bins shipping_bins_cleared_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_bins
    ADD CONSTRAINT shipping_bins_cleared_by_id_fkey FOREIGN KEY (cleared_by_id) REFERENCES public.users(id);


--
-- Name: shipping_bins shipping_bins_delivery_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_bins
    ADD CONSTRAINT shipping_bins_delivery_location_id_fkey FOREIGN KEY (delivery_location_id) REFERENCES public.delivery_locations(id);


--
-- Name: shipping_bins shipping_bins_shipping_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_bins
    ADD CONSTRAINT shipping_bins_shipping_job_id_fkey FOREIGN KEY (shipping_job_id) REFERENCES public.shipping_jobs(id);


--
-- Name: shipping_jobs shipping_jobs_assigned_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_jobs
    ADD CONSTRAINT shipping_jobs_assigned_user_id_fkey FOREIGN KEY (assigned_user_id) REFERENCES public.users(id);


--
-- Name: shipping_jobs shipping_jobs_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_jobs
    ADD CONSTRAINT shipping_jobs_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: sides sides_aisle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sides
    ADD CONSTRAINT sides_aisle_id_fkey FOREIGN KEY (aisle_id) REFERENCES public.aisles(id);


--
-- Name: sides sides_side_orientation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sides
    ADD CONSTRAINT sides_side_orientation_id_fkey FOREIGN KEY (side_orientation_id) REFERENCES public.side_orientations(id);


--
-- Name: trays tray_conveyance_bin_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT tray_conveyance_bin_fk FOREIGN KEY (conveyance_bin_id) REFERENCES public.conveyance_bins(id);


--
-- Name: tray_withdrawals tray_withdrawals_tray_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tray_withdrawals
    ADD CONSTRAINT tray_withdrawals_tray_id_fkey FOREIGN KEY (tray_id) REFERENCES public.trays(id);


--
-- Name: tray_withdrawals tray_withdrawals_withdraw_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tray_withdrawals
    ADD CONSTRAINT tray_withdrawals_withdraw_job_id_fkey FOREIGN KEY (withdraw_job_id) REFERENCES public.withdraw_jobs(id);


--
-- Name: trays trays_accession_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT trays_accession_job_id_fkey FOREIGN KEY (accession_job_id) REFERENCES public.accession_jobs(id);


--
-- Name: trays trays_barcode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT trays_barcode_id_fkey FOREIGN KEY (barcode_id) REFERENCES public.barcodes(id);


--
-- Name: trays trays_container_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT trays_container_type_id_fkey FOREIGN KEY (container_type_id) REFERENCES public.container_types(id);


--
-- Name: trays trays_media_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT trays_media_type_id_fkey FOREIGN KEY (media_type_id) REFERENCES public.media_types(id);


--
-- Name: trays trays_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT trays_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.owners(id);


--
-- Name: trays trays_shelf_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT trays_shelf_position_id_fkey FOREIGN KEY (shelf_position_id) REFERENCES public.shelf_positions(id);


--
-- Name: trays trays_size_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT trays_size_class_id_fkey FOREIGN KEY (size_class_id) REFERENCES public.size_class(id);


--
-- Name: trays trays_verification_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT trays_verification_job_id_fkey FOREIGN KEY (verification_job_id) REFERENCES public.verification_jobs(id);


--
-- Name: user_groups user_groups_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);


--
-- Name: user_groups user_groups_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_default_building_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_default_building_id_fkey FOREIGN KEY (default_building_id) REFERENCES public.buildings(id);


--
-- Name: verification_jobs verification_jobs_accession_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT verification_jobs_accession_job_id_fkey FOREIGN KEY (accession_job_id) REFERENCES public.accession_jobs(id);


--
-- Name: verification_jobs verification_jobs_container_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT verification_jobs_container_type_id_fkey FOREIGN KEY (container_type_id) REFERENCES public.container_types(id);


--
-- Name: verification_jobs verification_jobs_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_jobs
    ADD CONSTRAINT verification_jobs_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.owners(id);


--
-- Name: withdraw_jobs withdraw_jobs_assigned_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.withdraw_jobs
    ADD CONSTRAINT withdraw_jobs_assigned_user_id_fkey FOREIGN KEY (assigned_user_id) REFERENCES public.users(id);


--
-- Name: withdraw_jobs withdraw_jobs_pick_list_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.withdraw_jobs
    ADD CONSTRAINT withdraw_jobs_pick_list_id_fkey FOREIGN KEY (pick_list_id) REFERENCES public.pick_lists(id);


--
-- Name: items withdrawn_item_barcode_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT withdrawn_item_barcode_id FOREIGN KEY (withdrawn_barcode_id) REFERENCES public.barcodes(id);


--
-- Name: non_tray_items withdrawn_non_tray_item_barcode_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_tray_items
    ADD CONSTRAINT withdrawn_non_tray_item_barcode_id FOREIGN KEY (withdrawn_barcode_id) REFERENCES public.barcodes(id);


--
-- Name: trays withdrawn_tray_barcode_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trays
    ADD CONSTRAINT withdrawn_tray_barcode_id FOREIGN KEY (withdrawn_barcode_id) REFERENCES public.barcodes(id);


--
-- PostgreSQL database dump complete
--

