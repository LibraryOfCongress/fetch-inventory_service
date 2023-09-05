from fastapi import FastAPI
from os import environ as env

from app.routers import examples


app = FastAPI()


@app.get("/")
async def root():
    return {"message": f"{env['APP_NAME']} {env['APP_ENVIRONMENT']} environment api root"}

app.include_router(examples.router)
