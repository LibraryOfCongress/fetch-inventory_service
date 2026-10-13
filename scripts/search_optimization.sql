-- FETCH2 Production Optimization Script (Barcode & Workflow)
-- Target: PostgreSQL 14+
-- Focus: 10M Scale Barcode lookups, Request Tracking, Facility Walk-Order, and Space Reporting

-- 1. Item Barcode Optimization (10M Scale)
-- Covers both Standard Tray Items and Non-Tray Items
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_barcode_id ON items (barcode_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_non_tray_items_barcode_id ON non_tray_items (barcode_id);

-- 2. Request Tracking Optimization (Millions of rows over time)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_requests_status ON requests (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_requests_item_id ON requests (item_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_requests_non_tray_item_id ON requests (non_tray_item_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_requests_create_dt ON requests (create_dt);

-- 3. Inventory Infrastructure (600k Trays / 100k Shelves)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trays_barcode_id ON trays (barcode_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shelves_barcode_id ON shelves (barcode_id);

-- 4. Facility Walk-Order Optimization
-- Handles custom 'sort_priority' logic for non-linear layouts.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_aisles_walk_order ON aisles (building_id, COALESCE(sort_priority, id));
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ladders_walk_order ON ladders (building_id, aisle_id, COALESCE(sort_priority, id));
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shelves_master_walk_order ON shelves (building_id, aisle_id, ladder_id, COALESCE(sort_priority, id));

-- 5. Open Locations Report Optimization (Space Planning)
-- Optimizes the search for available space by Owner, Height, and Size Class.

-- Index the 'link' between Size Class and Shelf Type
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shelf_types_size_class ON shelf_types (size_class_id);

-- Partial index for shelves that actually have space (>0)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shelves_open_space_report 
ON shelves (owner_id, height, shelf_type_id, available_space) 
WHERE (available_space > 0);

-- 6. Workflow Job Optimization (Snappy Dashboards)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shelving_jobs_status ON shelving_jobs (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shipping_jobs_status ON shipping_jobs (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verification_jobs_status ON verification_jobs (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accession_jobs_status ON accession_jobs (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pick_lists_status ON pick_lists (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_refile_jobs_status ON refile_jobs (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_withdraw_jobs_status ON withdraw_jobs (status);

-- 7. Analyze to update statistics
ANALYZE items;
ANALYZE non_tray_items;
ANALYZE requests;
ANALYZE trays;
ANALYZE shelves;
ANALYZE shelving_jobs;
ANALYZE shipping_jobs;
ANALYZE verification_jobs;
ANALYZE accession_jobs;
ANALYZE pick_lists;
ANALYZE refile_jobs;
ANALYZE withdraw_jobs;
ANALYZE aisles;
ANALYZE ladders;
ANALYZE shelf_types;
