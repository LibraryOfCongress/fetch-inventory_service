from pydantic import BaseModel, ConfigDict


class LegacyUserInput(BaseModel):
    email: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "fbaggins@example.com"
            }
        }
    )
