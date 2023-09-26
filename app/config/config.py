from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Override in env. Default values are local
    APP_NAME: str = "FETCH"
    APP_ENVIRONMENT: str = "local"

    class Config:
        env_file=".env"

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    print(f"Loading settings for {settings.APP_ENVIRONMENT}")
    return settings
