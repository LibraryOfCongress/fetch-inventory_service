from typing import List

from pydantic import Json
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()


class Settings(BaseSettings):
    # Override in env. Default values are local
    APP_NAME: str = "FETCH"
    APP_ENVIRONMENT: str = "local"
    TIMEZONE: str = "America/New_York"
    IDP_ENTITY_ID: str = "https://idp.example.net/12345-ffff/"
    IDP_LOGIN_URL: str = "https://login.example.com/12345-fff/saml2"
    VUE_HOST: str = "https://localhost:8000"
    DATABASE_URL: str = (
        "postgresql://postgres:postgres@inventory-database:5432/inventory_service"
    )
    # migration_url = database_url except in local
    MIGRATION_URL: str = (
        "postgresql://postgres:postgres@localhost:5432/inventory_service"
    )
    ENABLE_ORM_SQL_LOGGING: bool = False
    # Allowed origins for CORS
    ALLOWED_ORIGINS_REGEX: str = "https://*\.example\.com, http://*\.example\.com"
    ALLOWED_ORIGINS: str = "http://127.0.0.1:8080,https://127.0.0.1:8080,http://localhost:8000,https://localhost:8000,http://localhost:3000,https://localhost:3000,http://localhost:4000"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    settings.ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS.split(",")

    print(f"Loading settings for {settings.APP_ENVIRONMENT}")
    return settings
