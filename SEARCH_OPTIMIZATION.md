# Production Optimization Guide (10M+ Scale)

This guide explains how to optimize the FETCH2 database for high-performance barcode lookups, request management, physical facility walk-orders, and space planning reports.

## The Objective: Sub-Millisecond Performance
At a scale of 10 million items, standard database tables can become slow. This guide implements **B-Tree**, **Composite Expression**, and **Partial** indexes to ensure the system remains "instant" for the users.

## 1. High-Volume Barcode Lookups
Scanning a barcode (Item, Tray, or Shelf) is the most frequent operation in the facility.
- **Tables Optimized:** `items`, `non_tray_items`, `trays`, `shelves`.

## 2. Request Tracking (Millions of Rows)
The `requests` table grows by 180,000+ rows per year. We index `status`, `create_dt`, and `item_id` so that the dashboard remains fast for years to come.

## 3. Physical Walk-Order (Hierarchical Sorting)
Ensures Pick Lists and Shelving Jobs are sorted in the most efficient physical path (Building -> Aisle -> Ladder -> Shelf).
- **Custom Sort Priority:** Uses `COALESCE(sort_priority, id)` logic to respect custom facility layouts.
- **Multi-Building Support:** All walk-order indexes use `building_id` as the leading column.

## 4. Open Locations Report (Space Planning)
Optimizes the search for available shelving based on **Owner**, **Size Class**, and **Shelf Height**.
- **Partial Indexing:** By using `WHERE (available_space > 0)`, the database only tracks shelves that actually have room, keeping the index small and fast.
- **Joined Optimization:** We index the link between `Size Class` and `Shelf Type` to make the space-finder report near-instant.

## Implementation Instructions

### Step 1: Run the Optimization Script
Connect to your production or staging database and execute the optimization script:
```bash
# Example using psql
psql -h your-db-host -U postgres -d inventory_service -f fetch-inventory_service/scripts/search_optimization.sql
```

### Step 2: Verify Index Usage
Run an `EXPLAIN ANALYZE` command to confirm the speed boost:
```sql
-- Check Open Locations speed
EXPLAIN ANALYZE 
SELECT * FROM shelves s 
JOIN shelf_types st ON s.shelf_type_id = st.id 
WHERE s.owner_id = 1 AND st.size_class_id = 2 AND s.available_space > 0;
```

### Step 3: Monitor RAM Usage
*   **Recommended RAM:** 32GB (for a 10M item facility).
*   **Why:** Ensures the database can store all critical indexes in the **PostgreSQL Buffer Cache**.

## Maintenance
- **Autovacuum**: Keep enabled to clean "dead rows."
- **Statistics**: The `ANALYZE` command ensures the Query Planner uses the best path.
