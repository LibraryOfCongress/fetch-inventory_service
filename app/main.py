from fastapi import FastAPI

from app.config.config import get_settings
from app.routers import buildings, modules, module_numbers


app = FastAPI()


@app.get("/")
async def root():
    return {"message": f"{get_settings().APP_NAME} Inventory Service {get_settings().APP_ENVIRONMENT} environment api root"}

# order matters for route matching [nested before base]
app.include_router(buildings.router)
app.include_router(module_numbers.router)
app.include_router(modules.router)
