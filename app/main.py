import subprocess
from contextlib import asynccontextmanager
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from alembic.config import Config
from alembic import command

from alembic.config import Config
from alembic import command

from app.middlware import log_middleware
from app.config.config import get_settings
from app.config.exceptions import (
    BadRequest,
    NotFound,
    ValidationException,
    InternalServerError,
    NotAuthorized,
    Forbidden,
    bad_request_exception_handler,
    not_found_exception_handler,
    validation_exception_handler,
    internal_server_error_exception_handler,
    not_authorized_exception_handler,
    forbidden_exception_handler,
)
from app.routers import (
    buildings,
    modules,
    module_numbers,
    aisles,
    aisle_numbers,
    sides,
    side_orientations,
    barcode_types,
    barcodes,
    ladder_numbers,
    ladders,
    shelf_numbers,
    shelf_position_numbers,
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
    shelving_jobs_tray_association,
    shelving_jobs_item_association,
)


def alembic_context():
    alembic_cfg = Config("alembic.ini")
    try:
        # Run migrations
        print("Migrating...")
        command.upgrade(alembic_cfg, "head")

        if get_settings().APP_ENVIRONMENT not in ["debug"]:
            # Create Schema-Docs
            print("Updating Schema Docs...")
            at_pos = get_settings().DATABASE_URL.find("@") + 1
            last_colon_pos = get_settings().DATABASE_URL.rfind(":")
            db_host = get_settings().DATABASE_URL[at_pos:last_colon_pos]
            create_schemaspy = [
                "java",
                "-jar",
                "/code/schemaspy.jar",
                "-t",
                "pgsql11",
                "-dp",
                "/code/postgresql.jar",
                "-o",
                "/code/schema-docs",
                "-u",
                "postgres",
                "-p",
                "postgres",
                "-db",
                "inventory_service",
                "-s",
                "public",
                "-host",
                f"{db_host}",
                "-port",
                "5432",
            ]
            subprocess.run(create_schemaspy)
    except Exception as e:
        print(f"{e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    alembic_context()
    if get_settings().APP_ENVIRONMENT not in ["debug"]:
        app.mount(
            "/schema",
            StaticFiles(directory="/code/schema-docs", html=True),
            name="schema-docs",
        )
    yield
    print("Shutting down...")


app = FastAPI(lifespan=lifespan)

# add log middleware
app.add_middleware(BaseHTTPMiddleware, dispatch=log_middleware)

# add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=get_settings().ALLOWED_ORIGINS_REGEX,
    allow_origins=get_settings().ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": f"{get_settings().APP_NAME} Inventory Service {get_settings().APP_ENVIRONMENT} environment api root"
    }


# app fallback exception handling
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"detail": str(exc.detail)}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return JSONResponse({"detail": str(exc)}, status_code=500)

# Register custom exception handlers
app.exception_handler(BadRequest)(bad_request_exception_handler)
app.exception_handler(NotFound)(not_found_exception_handler)
app.exception_handler(ValidationException)(validation_exception_handler)
app.exception_handler(InternalServerError)(internal_server_error_exception_handler)
app.exception_handler(NotAuthorized)(not_authorized_exception_handler)
app.exception_handler(Forbidden)(forbidden_exception_handler)

# order matters for route matching [nested before base]
app.include_router(buildings.router)
app.include_router(module_numbers.router)
app.include_router(modules.router)
app.include_router(aisle_numbers.router)
app.include_router(aisles.router)
app.include_router(side_orientations.router)
app.include_router(sides.router)
app.include_router(barcode_types.router)
app.include_router(barcodes.router)
app.include_router(ladder_numbers.router)
app.include_router(ladders.router)
app.include_router(container_types.router)
app.include_router(shelf_position_numbers.router)
app.include_router(shelf_positions.router)
app.include_router(shelf_numbers.router)
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
app.include_router(shelving_jobs_tray_association.router)
app.include_router(shelving_jobs_item_association.router)
app.include_router(shelving_jobs.router)
add_pagination(app)
