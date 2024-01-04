from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from alembic.config import Config
from alembic import command

from alembic.config import Config
from alembic import command

from app.config.config import get_settings
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
    accession_jobs
)


def alembic_context():
    alembic_cfg = Config("alembic.ini")
    try:
        print("Migrating...")
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    alembic_context()
    yield
    print("Shutting down...")


app = FastAPI(lifespan=lifespan)

# add CORS
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


# Serve the schema documentation
app.mount("/schema", StaticFiles(directory="/code/schema-docs", html=True), name="schema-docs")


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

add_pagination(app)
