from pydantic import BaseModel


class BatchUploadInput(BaseModel):
    file: str

    class Config:
        json_schema_extra = {
            "example": {
                "file": "base64 encoded file"
            }
        }
