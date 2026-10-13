# /code/app/main.py - FINAL, STABLE VERSION

import subprocess
import os, sys

# --- CRITICAL FIX: Ensure package path resolution works for Uvicorn/Alembic ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import importlib
import pkgutil

from app.middleware import JWTMiddleware

from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import logging
import time

# Ensure all models are imported/registered
import app.models.all

from alembic.config import Config
from alembic import command

from app.config.config import get_settings
from sqlalchemy.exc import DBAPIError
from app.config.exceptions import (
    BadRequest,
    NotFound,
    ValidationException,
    InternalServerError,
    NotAuthorized,
    Forbidden,
    MethodNotAllowed,
    bad_request_exception_handler,
    not_found_exception_handler,
    validation_exception_handler,
    internal_server_error_exception_handler,
    not_authorized_exception_handler,
    forbidden_exception_handler,
    method_not_allowed_exception_handler,
    unhandled_exception_handler,
)
from app.routers import (
    buildings,
    modules,
    aisles,
    sides,
    side_orientations,
    barcode_types,
    barcodes,
    ladders,
    shelves,
    container_types,
    shelf_positions,
    owner_tiers,
    owners,
    accession_jobs,
    verification_jobs,
    trays,
    media_types,
    size_class,
    conveyance_bins,
    items,
    subcollection,
    non_tray_items,
    shelving_jobs,
    users,
    groups,
    permissions,
    request_types,
    priorities,
    delivery_locations,
    requests,
    pick_lists,
    refile_queue,
    refile_jobs,
    withdraw_jobs,
    auth,
    status,
    batch_upload,
    shelf_types,
    reporting,
    audit_trails,
    verification_changes,
    item_retrieval_events,
    non_tray_item_retrieval_events,
    system_settings,
    shipping_jobs,
    ils_configurations,
    ils_sync_errors,
)


def _force_load_all_models():
    """Forces load of all model modules to ensure Base.metadata is populated."""
    try:
        models_package = importlib.import_module('app.models')
        for module_loader, name, is_pkg in pkgutil.walk_packages(
            models_package.__path__,
            models_package.__name__ + '.'
        ):
            importlib.import_module(name)
    except Exception as e:
        print(f"Warning: Model discovery failure in main.py: {e}")
        pass


def alembic_context():
    # CRITICAL: Force-load models before Alembic tries to configure metadata
    _force_load_all_models()

    alembic_cfg = Config("alembic.ini")
    try:
        print("Running Alembic migrations...")
        command.upgrade(alembic_cfg, "head")
        print("Migrations complete.")
    except Exception as e:
        print(f"Startup Error: {e}")
        # Re-raise because if the DB migration fails, the app is broken.
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup
    alembic_context()

    # Seed permissions if any are missing (idempotent)
    from app.seed.seed_permissions_adhoc import seed_new_permissions
    try:
        print("Checking for new permissions...")
        seed_new_permissions()
        print("Permission check complete.")
    except Exception as e:
        # Non-fatal - log and continue
        print(f"Warning: Permission seeding encountered an error: {e}")
        print("Continuing with application startup...")

    # SchemaSpy removed from production image. If re-enabled in a dev environment,
    # mount schema docs here:
    # if os.path.isdir("/code/schema-docs"):
    #     app.mount("/schema", StaticFiles(directory="/code/schema-docs", html=True), name="schema-docs")

    # Start background scheduler
    try:
        print("Importing scheduler module...")
        from app.scheduler import init_scheduler
        print("Initializing scheduler...")
        init_scheduler()
        print("Scheduler initialization complete.")
    except Exception as e:
        import traceback
        print(f"Warning: Scheduler failed to start: {e}")
        traceback.print_exc()

    yield
    print("Shutting down...")


app = FastAPI(
    lifespan=lifespan,
    # Don't issue 307 trailing-slash redirects. Our LB does not forward
    # X-Forwarded-Proto reliably, so the auto-generated Location header
    # comes back http:// and gets blocked as Mixed Content. With this
    # disabled, trailing-slash mismatches return 404 instead -- making
    # the bug visible at the frontend rather than silently broken.
    redirect_slashes=False,
    debug=True if get_settings().APP_ENVIRONMENT == "debug" else False
)


class ForceHttpsRedirectMiddleware(BaseHTTPMiddleware):
    """Defense-in-depth for environments where the load balancer does not
    pass X-Forwarded-Proto. Rewrites any outgoing 3xx Location header
    from http:// to https:// for our canonical hosts. Doesn't fire when
    the response Location is already https or relative.

    Only active when APP_ENVIRONMENT is not local/debug -- local dev runs
    over plain http intentionally.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if 300 <= response.status_code < 400:
            loc = response.headers.get("location")
            if loc and loc.startswith("http://"):
                env = get_settings().APP_ENVIRONMENT
                if env not in ("local", "debug"):
                    response.headers["location"] = "https://" + loc[len("http://"):]
        return response

# add log and auth check middleware first
app.add_middleware(JWTMiddleware)

# add CORS middleware second
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=get_settings().ALLOWED_ORIGINS_REGEX,
    allow_origins=get_settings().ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ProxyHeadersMiddleware -- read X-Forwarded-Proto/-For from the ingress
# and update the ASGI scope. Kept as a best-effort for environments where
# the LB DOES forward proto headers (test, stage, prod). On dev where the
# LB strips X-Forwarded-Proto, this is a no-op -- ForceHttpsRedirectMiddleware
# below picks up the slack.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Belt-and-suspenders: rewrite any 3xx Location header from http://
# to https:// for non-local environments. Catches every redirect class,
# not just trailing-slash. See class docstring above.
app.add_middleware(ForceHttpsRedirectMiddleware)


@app.get("/")
async def root():
    return {
        "message": f"{get_settings().APP_NAME} Inventory Service {get_settings().APP_ENVIRONMENT} environment api root"
    }


# app fallback exception handling
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"detail": str(exc.detail)}, status_code=exc.status_code)


# Register custom exception handlers
app.exception_handler(BadRequest)(bad_request_exception_handler)
app.exception_handler(NotFound)(not_found_exception_handler)
app.exception_handler(ValidationException)(validation_exception_handler)
app.exception_handler(InternalServerError)(internal_server_error_exception_handler)
app.exception_handler(NotAuthorized)(not_authorized_exception_handler)
app.exception_handler(Forbidden)(forbidden_exception_handler)
app.exception_handler(MethodNotAllowed)(method_not_allowed_exception_handler)
app.exception_handler(DBAPIError)(unhandled_exception_handler)
app.exception_handler(Exception)(unhandled_exception_handler)

# order matters for route matching [nested before base]
app.include_router(buildings.router)
app.include_router(modules.router)
app.include_router(aisles.router)
app.include_router(side_orientations.router)
app.include_router(sides.router)
app.include_router(barcode_types.router)
app.include_router(barcodes.router)
app.include_router(ladders.router)
app.include_router(container_types.router)
app.include_router(shelf_positions.router)
app.include_router(shelf_types.router)
app.include_router(shelves.router)
app.include_router(owner_tiers.router)
app.include_router(owners.router)
app.include_router(accession_jobs.router)
app.include_router(verification_jobs.router)
app.include_router(trays.router)
app.include_router(media_types.router)
app.include_router(size_class.router)
app.include_router(conveyance_bins.router)
app.include_router(items.router)
app.include_router(subcollection.router)
app.include_router(non_tray_items.router)
app.include_router(shelving_jobs.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(permissions.router)
app.include_router(request_types.router)
app.include_router(priorities.router)
app.include_router(delivery_locations.router)
app.include_router(requests.router)
app.include_router(pick_lists.router)
app.include_router(refile_queue.router)
app.include_router(refile_jobs.router)
app.include_router(withdraw_jobs.router)
app.include_router(auth.router)
app.include_router(status.router)
app.include_router(batch_upload.router)
app.include_router(reporting.router)
app.include_router(audit_trails.router)
app.include_router(verification_changes.router)
app.include_router(item_retrieval_events.router)
app.include_router(non_tray_item_retrieval_events.router)
app.include_router(system_settings.router)
app.include_router(shipping_jobs.router)
app.include_router(ils_configurations.router)
app.include_router(ils_sync_errors.router)

add_pagination(app)
