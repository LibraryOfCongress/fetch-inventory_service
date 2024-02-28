from pydantic import BaseModel
from typing import Optional


class ShelvingJobTrayAssociationInput(BaseModel):
    verified: bool
    shelf_position_proposed_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    shelving_job_id: Optional[int] = None
    tray_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "verified": True,
                "shelf_position_proposed_id": 1,
                "shelf_position_id": 1,
                "shelving_job_id": 1,
                "tray_id": 1
            }
        }


class ShelvingJobTrayAssociationUpdateInput(BaseModel):
    verified: Optional[bool] = None
    shelf_position_proposed_id: Optional[int] = None
    shelf_position_id: Optional[int] = None
    shelving_job_id: Optional[int] = None
    tray_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "verified": True,
                "shelf_position_proposed_id": 1,
                "shelf_position_id": 1,
                "shelving_job_id": 1,
                "tray_id": 1
            }
        }


class ShelvingJobTrayAssociationBaseOutput(BaseModel):
    verified: bool
    shelving_job_id: int
    tray_id: int


class ShelvingJobTrayAssociationListOutput(ShelvingJobTrayAssociationBaseOutput):
    class Config:
        json_schema_extra = {
            "example": {
                "verified": True,
                "shelving_job_id": 1,
                "tray_id": 1
            }
        }


class ShelvingJobTrayAssociationDetailOutput(ShelvingJobTrayAssociationBaseOutput):
    shelf_position_proposed_id: Optional[int] = None
    shelf_position_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "verified": True,
                "shelf_position_proposed_id": 1,
                "shelf_position_id": 1,
                "shelving_job_id": 1,
                "tray_id": 1
            }
        }
