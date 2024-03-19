from fastapi import APIRouter


from app.config.config import get_settings


router = APIRouter(
    prefix="/env",
    tags=["env check"],
)

@router.get("/", response_model=dict)
def get_env_info():
    app_settings = get_settings()
    settings_dict = app_settings.model_dump()
    settings_dict['env_file'] = app_settings.Config.env_file
    return settings_dict
