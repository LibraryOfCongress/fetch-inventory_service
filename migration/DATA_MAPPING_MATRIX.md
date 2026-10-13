# Data Mapping Matrix: LC to FETCH2

This document defines the mapping between the legacy Library of Congress (LC) database and the modern FETCH2 database for the ETL migration.

## 1. Direct Table Mappings (Topological Order)

The following tables should be migrated in this specific order to maintain foreign key integrity.

### Level 1: Independent Tables
| LC Table | FETCH2 Table | Transformation Logic |
| :--- | :--- | :--- |
| `users` | `users` | Added `default_building_id` (default NULL). |
| `groups` | `groups` | No major changes. |
| `owners` | `owners` | Added `ils_configuration_id` (default NULL). |
| `buildings` | `buildings` | No major changes. |
| `size_classes` | `size_classes` | No major changes. |
| `container_types` | `container_types` | No major changes. |
| `media_types` | `media_types` | No major changes. |
| `aisle_numbers` | N/A | **Lookup Table.** Used to populate `aisles.aisle_number`. |
| `ladder_numbers` | N/A | **Lookup Table.** Used to populate `ladders.ladder_number`. |
| `shelf_numbers` | N/A | **Lookup Table.** Used to populate `shelves.shelf_number`. |
| `shelf_position_numbers` | N/A | **Lookup Table.** Used to populate `shelf_positions.position_number`. |

### Level 2: Physical Hierarchy
| LC Table | FETCH2 Table | Transformation Logic |
| :--- | :--- | :--- |
| `modules` | `modules` | No major changes. |
| `aisles` | `aisles` | Join with `aisle_numbers` to populate `aisle_number`. Drop `aisle_number_id`. |
| `ladders` | `ladders` | Join with `ladder_numbers` to populate `ladder_number`. Drop `ladder_number_id`. |
| `sides` | `sides` | No major changes. |
| `shelves` | `shelves` | Join with `shelf_numbers` to populate `shelf_number`. Drop `shelf_number_id`, `location`, `internal_location`. |
| `shelf_positions` | `shelf_positions` | Join with `shelf_position_numbers` to populate `position_number`. Drop `shelf_position_number_id`, `location`, `internal_location`. |

### Level 3: Inventory
| LC Table | FETCH2 Table | Transformation Logic |
| :--- | :--- | :--- |
| `trays` | `trays` | No major changes. |
| `items` | `items` | Added `ils_sync_state` (default 'IN_SYNC'), `scanned_for_shipping` (default False), `shipping_bin_id` (NULL). |
| `non_tray_items` | `non_tray_items` | Added `ils_sync_state` (default 'IN_SYNC'), `scanned_for_shipping` (default False), `shipping_bin_id` (NULL). |

### Level 4: Workflows
| LC Table | FETCH2 Table | Transformation Logic |
| :--- | :--- | :--- |
| `accession_jobs` | `accession_jobs` | Rename `user_id` -> `assigned_user_id`. |
| `pick_lists` | `pick_lists` | Rename `user_id` -> `assigned_user_id`. |
| `shelving_jobs` | `shelving_jobs` | Rename `user_id` -> `assigned_user_id`. Added `mode`, `allow_*` columns (set defaults). |
| `verification_jobs` | `verification_jobs` | Rename `user_id` -> `assigned_user_id`. |
| `requests` | `requests` | Added `deleted` (default False). |

---

## 2. Key Transformations

### Renamed Columns (The "Assigned User" Shift)
In FETCH2, the primary user associated with a job was renamed for clarity.
- **Tables affected:** `accession_jobs`, `pick_lists`, `shelving_jobs`, `verification_jobs`.
- **Mapping:** `lc.user_id` -> `f2.assigned_user_id`.

### Flattening the Number Hierarchy
LC used lookup tables for simple numbers (Aisle 1, Ladder 2, etc.). FETCH2 stores these directly as integers.
- **Logic:** `SELECT t.*, n.number AS actual_number FROM lc_table t JOIN lookup_table n ON t.number_id = n.id`.
- **Impact:** Significant reduction in join complexity for future queries.

### Audit Log Evolution
The `audit_log` table has expanded significantly in FETCH2.
- **Decision:** Legacy audit data is typically "frozen" or migrated into the new schema with generic `job_type` and `event_type` tags. We will implement a best-effort mapping for historical audit records.

---

## 3. New Tables (Start Empty)
These tables will be created by migrations but will contain no data initially:
- `shipping_jobs`
- `shipping_bins`
- `ils_configurations`
- `ils_sync_errors`
- `scheduled_exports`
- `export_history`
- `system_settings`
- `owner_delivery_locations`
- `shelving_job_containers` (This table replaces the old many-to-many relationship in shelving jobs)
