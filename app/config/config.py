
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Override in env. Default values are local
    APP_NAME: str = "FETCH"
    APP_ENVIRONMENT: str = "local"
    TIMEZONE: str = "America/New_York"
    DATABASE_URL: str = "postgresql://postgres:postgres@host.docker.internal:5432/inventory_service"
    # migration_url = database_url except in local
    MIGRATION_URL: str = "postgresql://postgres:postgres@localhost:5432/inventory_service"
    ENABLE_ORM_SQL_LOGGING: bool = True

    class Config:
        env_file=".env"

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    print(f"Loading settings for {settings.APP_ENVIRONMENT}")
    return settings
