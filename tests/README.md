# FETCH2 Inventory Service - Test Suite Guide

This directory contains the modernized, behavior-driven test suite for the FETCH2 Inventory Service. 


---

## 1. Domain & Entity Logic Tests (`tests/domain/test_inventory_entities.py`)
**What it does:** Tests the core SQLAlchemy models, database constraints, and lowest-level business rules *without* relying on FastAPI or the web layer.

**Coverage Examples:** 
- Ensuring `Shelf` capacity calculation logic works correctly when `ShelfType` sizes change.
- Validating global `Barcode` uniqueness.
- Ensuring polymorphic identities (like `Item` vs `NonTrayItem`) interact smoothly.

**How to use it in the future:**
Whenever you add a new database model, introduce a new database constraint, or write complex native Python functions (such as calculating dimensions or validating formats), add tests here. 

> **Rule of Thumb:** If the feature can be tested purely with Python and a database session (without needing an HTTP request), it belongs here.

---

## 2. Complex Hierarchy & Cascade Tests (`tests/domain/test_location_hierarchy.py`)
**What it does:** Specifically focuses on the deep physical relationships between `Building` → `Module` → `Aisle` → `Side` → `Ladder` → `Shelf`. 

**Coverage Examples:**
- Ensuring you can't have duplicate Aisle numbers inside the same Module.
- Proving that deleting a Building correctly cascades and prevents accidental orphaned shelves.

**How to use it in the future:**
Use this whenever the physical or logical structure of the warehouse changes. If you add "Zones" or "Bins," or if you change the rules about what can physically fit on a shelf, those validation tests should go here.

---

## 3. API-Level End-to-End Workflow Tests (`tests/domain/test_job_workflows.py`)
**What it does:** These are the most powerful tests in the system. They use FastAPI's `TestClient` to simulate a user actually moving items through the warehouse utilizing the 7 core jobs (Accession, Verification, Shelving, Picklist, Shipping, Refile, Withdraw).

**Coverage Examples:**
- Proving that when an Accession scan is completed via `PATCH`, the `Item` status changes, and a `VerificationJob` is automatically spawned by a background task.
- Enforcing state transitions (e.g., proving that the API *rejects* an attempt to ship an item if its status isn't `Retrieved`).

**How to use it in the future:**
These tests represent your **Integration Layer**. Whenever you alter the "flow" of a warehouse job (e.g., adding a new QA step between Verification and Shelving, or creating an entirely new Job Type), you must write a workflow test here. These tests ensure that the API controllers, background tasks, and database transactions all interact correctly from the user's perspective. 

---

## 4. RBAC Security Tests (`tests/auth/test_rbac.py`)
**What it does:** Proves that the "front door" of the application is locked. It loops through the protected routers and guarantees that missing tokens or missing permissions yield `401 Unauthorized` or `403 Forbidden` responses.

**Coverage Examples:**
- Hitting `/accession-jobs/` with a user who only has the `can_access_reports` permission and making sure it is blocked.
- Verifying that users without an `Authorization` header are entirely denied access.

**How to use it in the future:**
When you add a new major domain feature (e.g., a new `/billing` router) and a corresponding permission (e.g., `can_view_billing_data`), add that route and permission to the `PROTECTED_ROUTES` list at the top of this file. The test suite will automatically generate mock users and verify the new route is secured.

---

## Summary for Future Development (TDD)
1. **Focus on Behavior, Not Endpoints:** Don't write tests just to prove `GET /something` returns a 200 JSON object. Write tests to prove that `POST /checkout` actually deducts inventory and triggers an email.
2. **Lean on the Global `conftest` Setup:** High effort was spent ensuring `conftest.py` spins up isolated database containers, resets the schema, and optionally injects a "SuperUser" mock for the API tests. Future tests can safely assume they are starting with a clean, fully-functioning database that won't accidentally poison the production schema.
3. **Trace the Layers on Failure:** 
   - If a workflow test fails but entity tests pass: The issue is likely in your FastAPI router or Background Task. 
   - If the entity test fails: The issue is fundamentally in your SQLAlchemy model or database constraint.
