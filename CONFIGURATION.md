# FETCH2 System Configuration Guide

This guide describes the configuration options available in the **Admin Dashboard** (`/admin`) that should be customized before using the system in a production environment. These settings control how FETCH2 manages inventory, shelving rules, user access, and external integrations.

> **Permission Required:** Access to the Admin panel requires the `can_access_admin` permission. Individual sections require additional permissions as noted below.

---

## Access & Identity

### Groups & Permissions
**Path:** Admin > Groups & Permissions
**Permission:** `can_manage_groups_and_permissions`

Groups are the foundation of the FETCH2 access control system. Every permission in the system is assigned to a **Group**, and users gain access to workflows by being added to groups.

**What to configure:**
- Create groups that match your organizational roles (e.g., "Accessioners", "Shelving Team", "Supervisors", "Administrators")
- For each group, assign the appropriate permissions from the full permission set
- Add users to their respective groups

**Example permission categories:**
- `can_access_accession`, `can_access_verification`, `can_access_shelving`, `can_access_picklist`, `can_access_refile`, `can_access_shipping`, `can_access_withdraw`
- `can_access_admin`, `can_manage_groups_and_permissions`, `can_manage_locations`, `can_manage_system_configurations`, `can_manage_list_configurations`
- `can_access_reports`, `can_access_request`, `can_access_item_detail`, `can_access_shelf_detail`, `can_access_tray_detail`

> **Important:** Users without any group assignments will have no access to any workflow. After the first login, administrators should immediately assign the initial user to an admin group.

### User Management
**Path:** Admin > User Management
**Permission:** `can_manage_groups_and_permissions`

View and manage all users who have logged into the system. Users are created automatically on first login (via SSO or legacy login), but their group memberships must be configured here or through the Groups panel.

---

## System Configurations

These settings affect core system behavior and are located under **Admin > System Configurations**.
**Permission:** `can_manage_system_configurations`

### ILS Integrations
**Path:** Admin > System Configurations > ILS Integrations

Configure connections to Integrated Library Systems (e.g., FOLIO, ALMA) for automated synchronization of item statuses during workflows.

**Configuration fields:**

| Field | Description |
|---|---|
| **Configuration Name** | A descriptive name for this ILS connection |
| **Adapter Type** | The ILS platform: `FOLIO`, `ALMA`, or `CUSTOM_MIDDLEWARE` |
| **Base URL** | The root API URL of the ILS instance |
| **Tenant ID** | The ILS tenant identifier (e.g., FOLIO tenant) |
| **Client ID** | OAuth 2.0 client ID for authentication |
| **Client Secret** | OAuth 2.0 client secret |
| **Token URL** | (Optional) Custom token endpoint if it differs from the standard path |
| **Service Point ID** | (FOLIO) The service point used for check-in and request operations |
| **Expected Shelved Status** | The ILS status string that represents a shelved item (e.g., "Available") |
| **Expected Refile Status** | The ILS status when items are queued for refile (e.g., "In Transit") |
| **Expected Picklist Status** | The ILS status when items are picked for retrieval (e.g., "In Transit") |
| **Integration Active** | Master toggle to enable/disable the connection |

> [!CAUTION]
> **Credential Safety:** `Client Secret` values are sensitive and should **never** be hardcoded in any local configuration files, docker-compose manifests, or plain-text scripts that are committed to version control. Always use a secure secret management solution for production credentials.

**Feature / Hook Toggles:**

| Toggle | Description |
|---|---|
| Enable Accession Sync | Sync item status with ILS during accession |
| Enable Shelving Sync | Sync item status with ILS during shelving |
| Enable Refile Sync | Perform ILS check-in when items are refiled |
| Enable Picklist Sync | Sync item status with ILS when pick lists are executed |
| Enable Requests Sync | Poll ILS for incoming requests |
| Enable Custom Meta JIT Pull | On-demand metadata lookup from ILS (performance-intensive) |

> **Note:** If you are not connecting to an ILS, you can skip this section entirely. The system will operate in standalone mode.

### Integration Issues
**Path:** Admin > System Diagnostics > Integration Issues

View and manage ILS synchronization errors. When an ILS hook fails (e.g., a check-in request returns an error), the error is logged here for administrator review and retry.

### Barcode Types
**Path:** Admin > System Configurations > Barcode Types

Define the barcode formats accepted by the system. Each barcode type has a **name** and an **allowed pattern** (regex) that validates scanned input.

**What to configure:**
- Define patterns for your item barcodes, tray barcodes, and shelf barcodes
- The pattern determines what strings the system will accept as valid scans

### Shelf Position Direction
**Path:** Admin > System Configurations > Shelf Position Direction

Controls the direction for **auto-assigning shelf positions** during direct-to-shelf shelving workflows.

| Option | Behavior |
|---|---|
| **Low to High** (default) | Positions are suggested starting from 1, then 2, 3, etc. |
| **High to Low** | Positions are suggested starting from the highest available (e.g., 15, 14, 13...) |

### Child Owner Shelving
**Path:** Admin > System Configurations > Child Owner Shelving

Controls whether items belonging to a **child owner** (in a tiered ownership hierarchy) can be shelved on shelves assigned to a **parent owner**.

| Setting | Behavior |
|---|---|
| **Disabled** (default) | Exact owner match is required (unless the shelf is Unassigned) |
| **Enabled** | Child owner items CAN be shelved on parent owner shelves |

> **Note:** Regardless of this setting, parent owner items can never be shelved on child owner shelves.

### Shipping Module
**Path:** Admin > System Configurations > Shipping Module

Enables or disables the Shipping workflow as an intermediate step between retrieval and delivery.

| Setting | Behavior |
|---|---|
| **Disabled** (default) | Items from completed Pick Lists are set directly to "Out" status |
| **Enabled** | Items from completed Pick Lists are set to "Retrieved" status, requiring a separate Shipping Job to move them to "Out" |

> **Important:** Enable this if your facility uses a shipping/delivery step between the storage area and the reading room or requesting patron.

---

## List Configurations

These are the reference data lists that appear as dropdown options throughout the system. They should be customized to match your organization's vocabulary and operational structure.
**Permission:** `can_manage_list_configurations`

All list configurations are managed through **Admin > List Configurations** and support Add, Edit, and Delete operations.

### Owners
Owners represent the organizations or divisions that own the stored materials. FETCH2 supports a **tiered ownership hierarchy** (e.g., Tier 1: "Library of Congress", Tier 2: "Congressional Research Services"). Owners are assigned to shelves and used for filtering and access control in workflows.

**Fields:** Name, Owner Tier, Parent Owner (for child tiers)

### Media Types
Categories of physical media stored in the facility (e.g., "Bound Volume", "Microfilm", "Photograph", "Map", "Audio Recording"). Used during accession to classify items.

**Fields:** Name

### Size Classes
Physical dimensions of items, used for determining which shelf types can accommodate them. Each size class has width, depth, and height measurements in inches.

**Fields:** Name, Short Name, Width, Depth, Height

### Shelf Types
Define the types of shelving available in your facility. Each shelf type is associated with a size class and determines what items can be stored on it. Shelf types also define the maximum capacity (number of positions) per shelf.

**Fields:** Type name, associated Size Class(es)

### Priorities
Priority levels for retrieval requests (e.g., "Normal", "Rush", "Emergency"). Used when creating requests and generating pick lists to determine processing order.

**Fields:** Value (priority name)

### Delivery Locations
Physical locations where retrieved items can be delivered (e.g., "Main Reading Room", "Researcher Lab A", "Loading Dock"). Used when creating requests to specify where items should go.

**Fields:** Name, Address

### Request Types
Categories of requests (e.g., "Patron Request", "Internal Transfer", "Exhibition Loan"). Used when creating retrieval requests to classify the purpose.

**Fields:** Type name

---

## Location Manager

**Path:** Admin > Location Manager
**Permission:** `can_manage_locations`

The Location Manager provides tools for creating and editing the physical storage hierarchy:

### Manage Locations
An interactive explorer for browsing and editing the full location hierarchy: **Building → Module → Aisle → Side → Ladder → Shelf → Shelf Position**. Individual locations can be edited (renamed, reassigned, etc.) through this interface.

### Bulk Create Shelves/Ladder
Upload a CSV file to create multiple shelves and ladders at once. Useful for initial facility setup or expansion.

### Bulk Edit Shelves
Bulk update properties of existing shelves (e.g., reassign owners, change shelf types) across a selection of locations.

---

## Recommended First-Time Setup Order

For a new FETCH2 deployment, configure in this order:

1. **Groups & Permissions** — Create an admin group and assign yourself
2. **Owners** — Define your ownership hierarchy
3. **Media Types** — Define what kinds of materials you store
4. **Size Classes** — Define the physical dimensions of your items
5. **Shelf Types** — Define shelf configurations using your size classes
6. **Barcode Types** — Define the barcode patterns for your facility
7. **Priorities** — Set up request priority levels
8. **Delivery Locations** — Add your reading rooms and delivery points
9. **Request Types** — Define your request categories
10. **Location Manager** — Build out your physical storage hierarchy (Building → Module → Aisle → Side → Ladder → Shelf)
11. **System Configurations** — Set shelf position direction, child owner shelving, and shipping module preferences
12. **ILS Integrations** — (Optional) Connect to your ILS if applicable
