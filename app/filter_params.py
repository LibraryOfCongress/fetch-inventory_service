# from fastapi import Query
from fastapi import Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class JobFilterParams(BaseModel):
    """
    Reusable query params across Jobs.
    Status is not included as the Enumerated options differ per job.
    """
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None
    user_id: Optional[int] = None
    workflow_id: Optional[int] = None
    created_by_id: Optional[int] = None


class ShelvingJobDiscrepancyParams(BaseModel):
    """
    Query params for Shelving Job Discrepancies
    """
    shelving_job_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    owner_id: Optional[int] = None
    size_class_id: Optional[int] = None
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None
    user_id: Optional[int] = None


class OpenLocationParams:
    """
    Query params for Open Locations Report.
    The underlying list query is against shelves
    with a shelf position join
    """
    def __init__(
        self,
        building_id: Optional[int] = None,
        module_id: Optional[int] = None,
        aisle_id: Optional[int] = None,
        side_id: Optional[int] = None,
        ladder_id: Optional[int] = None,
        height: Optional[float] = None,
        width: Optional[float] = None,
        depth: Optional[float] = None,
        show_partial: Optional[bool] = False,
        owner_id: list[int] = Query(default=None),
        size_class_id: list[int] = Query(default=None)
    ):
        self.building_id = building_id
        self.module_id = module_id
        self.aisle_id = aisle_id
        self.side_id = side_id
        self.ladder_id = ladder_id
        self.height = height
        self.width = width
        self.depth = depth
        self.show_partial = show_partial
        self.owner_id = owner_id
        self.size_class_id = size_class_id


class SortParams(BaseModel):
    """
    Query params for sorting
    """
    sort_by: Optional[str] = Query(default=None, description="Field to sort by")
    sort_order: Optional[str] = Query(default="asc", description="Sort order: 'asc' or 'desc'")


class AccessionedItemsParams:
    """
    Query params for Accessioned Items Report.
    """
    def __init__(self,
                 owner_id: list[int] = Query(default=None),
                 size_class_id: list[int] = Query(default=None),
                 media_type_id: list[int] = Query(default=None),
                 from_dt: Optional[datetime] = Query(default=None, description="Start accessioned date to "
                                                            "filter by."),
                 to_dt: Optional[datetime] = Query(default=None, description="End "
                                                                            "accessioned date to "
                                                            "filter by."),
                 ):
        self.owner_id = owner_id
        self.size_class_id = size_class_id
        self.media_type_id = media_type_id
        self.from_dt = from_dt
        self.to_dt = to_dt


class AisleItemsCountParams(BaseModel):
    """
    Query params for Aisle Items Count Report.
    """
    building_id: int = Query(..., description="ID of the building to filter aisles.")
    aisle_num_from: Optional[int] = Query(None, description="Starting aisle number.")
    aisle_num_to: Optional[int] = Query(None, description="Ending aisle number.")


class NonTrayItemsCountParams:
    """
    Query params for Non Tray Items Count Report.
    """
    def __init__(
        self,
        building_id: int = Query(..., description="ID of the building to filter."),
        module_id: int = Query(default=None, description="ID of the module to "
                                                         "filter."),
        owner_id: list[int] = Query(default=None),
        size_class_id: list[int] = Query(default=None),
        aisle_num_from: Optional[int] = Query(None, description="Starting aisle "
                                                                "number."),
        aisle_num_to: Optional[int] = Query(None, description="Ending aisle number."),
        from_dt: datetime = Query(default=None, description="Start shelved date to "
                                                            "filter by."),
        to_dt: datetime = Query(default=None, description="End shelved date to "
                                                          "filter by.")
    ):
        self.building_id = building_id
        self.module_id = module_id
        self.owner_id = owner_id
        self.size_class_id = size_class_id
        self.aisle_num_from = aisle_num_from
        self.aisle_num_to = aisle_num_to
        self.from_dt = from_dt
        self.to_dt = to_dt


class TrayItemCountParams:
    """
        Query params for Non Tray Items Count Report.
        """

    def __init__(
        self,
        building_id: int = Query(
            ..., description="ID of the building to filter "
                             "aisles."
            ),
        module_id: int = Query(default=None, description="ID of the module to "
                                                         "filter."),
        owner_id: list[int] = Query(default=None),
        aisle_num_from: Optional[int] = Query(
            None, description="Starting aisle "
                              "number."
            ),
        aisle_num_to: Optional[int] = Query(None, description="Ending aisle number."),
        from_dt: datetime = Query(
            default=None, description="Start shelved date to "
                                      "filter by."
            ),
        to_dt: datetime = Query(
            default=None, description="End shelved date to "
                                      "filter by."
            )
    ):
        self.building_id = building_id
        self.module_id = module_id
        self.owner_id = owner_id
        self.aisle_num_from = aisle_num_from
        self.aisle_num_to = aisle_num_to
        self.from_dt = from_dt
        self.to_dt = to_dt
