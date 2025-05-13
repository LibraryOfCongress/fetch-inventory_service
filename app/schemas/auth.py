from pydantic import BaseModel


class LegacyUserInput(BaseModel):
    email: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "fbaggins@example.com"
            }
        }
