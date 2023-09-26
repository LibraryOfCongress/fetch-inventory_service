from fastapi import FastAPI

from app.config.config import get_settings
from app.routers import examples


app = FastAPI()


@app.get("/")
async def root():
    return {"message": f"{get_settings().APP_NAME} Inventory Service {get_settings().APP_ENVIRONMENT} environment api root"}

app.include_router(examples.router)
