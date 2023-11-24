from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

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
    shelf_positions
)

app = FastAPI()

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

add_pagination(app)
