from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Override in env. Default values are local
    model_config = SettingsConfigDict(case_sensitive=True)
    APP_NAME: str = "FETCH"
    APP_ENVIRONMENT: str = "local"


settings = Settings()
