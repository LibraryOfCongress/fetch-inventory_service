from pydantic import BaseModel
from typing import Optional


class ShelvingJobItemAssociationInput(BaseModel):
    verified: bool
    shelf_position_proposed_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    shelving_job_id: Optional[int] = None
    item_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "verified": True,
                "shelf_position_proposed_id": 1,
                "shelf_position_id": 1,
                "shelving_job_id": 1,
                "item_id": 1,
            }
        }


class ShelvingJobItemAssociationUpdateInput(BaseModel):
    verified: Optional[bool] = None
    shelf_position_proposed_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    shelving_job_id: Optional[int] = None
    item_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "verified": True,
                "shelf_position_proposed_id": 1,
                "shelf_position_id": 1,
                "shelving_job_id": 1,
                "item_id": 1,
            }
        }


class ShelvingJobItemAssociationBaseOutput(BaseModel):
    verified: bool
    shelving_job_id: int
    item_id: int


class ShelvingJobItemAssociationListOutput(ShelvingJobItemAssociationBaseOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "verified": True,
                "shelving_job_id": 1,
                "item_id": 1
            }
        }


class ShelvingJobItemAssociationDetailOutput(ShelvingJobItemAssociationBaseOutput):
    shelf_position_proposed_id: Optional[int] = None
    shelf_position_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "verified": True,
                "shelf_position_proposed_id": 1,
                "shelf_position_id": 1,
                "shelving_job_id": 1,
                "item_id": 1,
            }
        }
