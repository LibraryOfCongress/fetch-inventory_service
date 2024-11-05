from typing import Optional
from pydantic import BaseModel


class AccessionItemsDetailOutput(BaseModel):
    owner_name: Optional[str] = "All"
    size_class_name: Optional[str] = "All"
    media_type_name: Optional[str] = "All"
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "owner_name": "All",
                "size_class_name": "All",
                "media_type_name": "All",
                "count": 1
            }
        }





