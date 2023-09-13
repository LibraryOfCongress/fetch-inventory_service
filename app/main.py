from fastapi import FastAPI

from app.config import config
from app.routers import examples


app = FastAPI()


@app.get("/")
async def root():
    return {"message": f"{config.settings.APP_NAME} Inventory Service {config.settings.APP_ENVIRONMENT} environment api root"}

app.include_router(examples.router)
