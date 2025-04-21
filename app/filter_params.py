# from fastapi import Query
from fastapi import Query
from pydantic import BaseModel

from typing import Optional, List, Type
from datetime import datetime

from app.models.accession_jobs import AccessionJobStatus
from app.models.items import ItemStatus
from app.models.requests import RequestStatus


class ItemFilterParams:
    """
    Reusable query params across Items.
    """

    def __init__(
        self,
        owner_id: List[int] = Query(
            default=None, description="ID of the user to filter " "items."
        ),
        owner: List[str] = Query(
            default=None, description="Name of the owner to filter items."
        ),
        size_class_id: List[int] = Query(
            default=None, description="ID of the size class " "to filter items."
        ),
        size_class: str = Query(
            default=None, description="Name of the size class to filter items."
        ),
        media_type_id: List[int] = Query(
            default=None, description="ID of the media type " "to filter items."
        ),
        media_type: str = Query(
            default=None, description="Name of the media type to filter items."
        ),
        barcode_value: List[str] = Query(
            default=None, description="Value of the barcode " "to filter items."
        ),
        from_dt: datetime = Query(
            default=None, description="Start Accession date to filter by."
        ),
        to_dt: datetime = Query(
            default=None, description="End Accession date to filter by."
        ),
        status: List[ItemStatus] = Query(
            default=None, description="Status to filter by."
        ),
    ):
        self.owner_id = owner_id
        self.owner = owner
        self.size_class_id = size_class_id
        self.size_class = size_class
        self.media_type_id = media_type_id
        self.media_type = media_type
        self.barcode_value = barcode_value
        self.from_dt = from_dt
        self.to_dt = to_dt
        self.status = status


class AuthFilterParams(BaseModel):
    """
    SSO params
    """

    preserve_route: Optional[str] = None


class ShelfFilterParams(BaseModel):
    """
    Reusable query params across Shelves.
    """

    building_id: Optional[int] = None
    module_id: Optional[int] = None
    aisle_id: Optional[int] = None
    side_id: Optional[int] = None
    ladder_id: Optional[int] = None
    shelf_id: Optional[int] = None
    owner_id: Optional[int] = None
    size_class_id: Optional[int] = None
    unassigned: Optional[int] = None
    shelf_location: Optional[int] = None
    barcode_value: Optional[str] = None
    owner: Optional[str] = None
    size_class: Optional[str] = None
    location: Optional[str] = None


class ModuleFilterParams(BaseModel):
    """
    Params for Module List.
    """

    building_id: Optional[int] = None
    building_name: Optional[str] = None


class AisleFilterParams(BaseModel):
    """
    Params for Aisle List.
    """

    module_number: Optional[str] = None
    building_id: Optional[int] = None
    module_id: Optional[int] = None


class SideFilterParams(BaseModel):
    """
    Params for Side List.
    """

    building_id: Optional[int] = None
    module_id: Optional[int] = None
    aisle_id: Optional[int] = None


class LadderFilterParams(BaseModel):
    """
    Params for Ladder List.
    """

    building_id: Optional[int] = None
    module_id: Optional[int] = None
    aisle_id: Optional[int] = None
    side_id: Optional[int] = None


class JobFilterParams:
    """
    Reusable query params across Jobs.
    Status is not included as the Enumerated options differ per job.
    """

    def __init__(
        self,
        queue: Optional[bool] = False,
        workflow_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        container_type: Optional[str] = None,
        trayed: Optional[bool] = None,
        assigned_user_id: Optional[int] = None,
        building_name: List[str] = Query(
            default=None, description="Building name to filter by."
        ),
        user_id: List[int] = Query(default=None, description="User ID to filter by."),
        assigned_user: List[str] = Query(
            default=None, description="Assigned " "user to filter by."
        ),
        status: List[str] = Query(default=None, description="Status to filter by."),
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ):
        self.queue = queue
        self.workflow_id = workflow_id
        self.created_by_id = created_by_id
        self.container_type = container_type
        self.trayed = trayed
        self.assigned_user_id = assigned_user_id
        self.building_name = building_name
        self.user_id = user_id
        self.assigned_user = assigned_user
        self.status = status
        self.from_dt = from_dt
        self.to_dt = to_dt


class RefileQueueParams:
    """
    Reusable query params across Refile Queue.
    """

    def __init__(
        self,
        building_id: Optional[int] = None,
        barcode_value: Optional[str] = None,
        media_type: list[str] = Query(
            default=None, description="Media type to filter by."
        ),
        owner: list[str] = Query(default=None, description="Owner to filter by."),
        size_class: list[str] = Query(
            default=None, description="Size class to filter by."
        ),
        container_type: list[str] = Query(
            default=None, description="Container type to filter by."
        ),
        item_location: Optional[str] = None,
        non_tray_item_location: Optional[str] = None,
    ):
        self.building_id = building_id
        self.barcode_value = barcode_value
        self.media_type = media_type
        self.owner = owner
        self.size_class = size_class
        self.container_type = container_type
        self.item_location = item_location
        self.non_tray_item_location = non_tray_item_location


class RequestFilterParams:
    """
    Reusable query params across Requests.
    """

    def __init__(
        self,
        status: List[RequestStatus] = Query(
            default=None, description="Status to filter by."
        ),
        building_id: Optional[int] = None,
        building_name: list[str] = Query(
            default=None, description="Building name to " "filter by."
        ),
        queue: Optional[bool] = False,
        unassociated_pick_list: Optional[bool] = False,
        requestor_name: Optional[str] = None,
        item_barcode: Optional[str] = None,
        non_tray_item_barcode: Optional[str] = None,
        barcode_value: Optional[str] = None,
        request_type: List[str] = Query(
            default=None, description="Request type to filter by."
        ),
        item_status: List[str] = Query(
            default=None, description="Item Status to " "filter " "by."
        ),
        priority: List[str] = Query(default=None, description="Priority to filter by."),
        media_type: List[str] = Query(
            default=None, description="Media type to filter by."
        ),
        external_request_id: List[str] = Query(default=None, description="External "
                                                                         "Requester "
                                                                         "ID to "
                                                                         "filter by."),
        delivery_location: List[str] = Query(
            default=None, description="Delivery location to filter by."
        ),
        item_location: Optional[str] = None,
        non_tray_item_location: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ):
        self.status = status
        self.item_status = item_status
        self.building_id = building_id
        self.building_name = building_name
        self.queue = queue
        self.unassociated_pick_list = unassociated_pick_list
        self.requestor_name = requestor_name
        self.barcode_value = barcode_value
        self.item_barcode = item_barcode
        self.non_tray_item_barcode = non_tray_item_barcode
        self.request_type = request_type
        self.priority = priority
        self.media_type = media_type
        self.external_request_id = external_request_id
        self.item_location = item_location
        self.non_tray_item_location = non_tray_item_location
        self.delivery_location = delivery_location
        self.from_dt = from_dt
        self.to_dt = to_dt


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
        size_class_id: list[int] = Query(default=None),
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
    sort_order: Optional[str] = Query(
        default="asc", description="Sort order: 'asc' or 'desc'"
    )


class AccessionedItemsParams:
    """
    Query params for Accessioned Items Report.
    """

    def __init__(
        self,
        owner_id: list[int] = Query(default=None),
        size_class_id: list[int] = Query(default=None),
        media_type_id: list[int] = Query(default=None),
        from_dt: Optional[datetime] = Query(
            default=None, description="Start accessioned date to " "filter by."
        ),
        to_dt: Optional[datetime] = Query(
            default=None, description="End " "accessioned date to " "filter by."
        ),
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
        module_id: int = Query(
            default=None, description="ID of the module to " "filter."
        ),
        owner_id: list[int] = Query(default=None),
        size_class_id: list[int] = Query(default=None),
        aisle_num_from: Optional[int] = Query(
            None, description="Starting aisle " "number."
        ),
        aisle_num_to: Optional[int] = Query(None, description="Ending aisle number."),
        from_dt: datetime = Query(
            default=None, description="Start shelved date to " "filter by."
        ),
        to_dt: datetime = Query(
            default=None, description="End shelved date to " "filter by."
        ),
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
            ..., description="ID of the building to filter " "aisles."
        ),
        module_id: int = Query(
            default=None, description="ID of the module to " "filter."
        ),
        owner_id: list[int] = Query(default=None),
        aisle_num_from: Optional[int] = Query(
            None, description="Starting aisle " "number."
        ),
        aisle_num_to: Optional[int] = Query(None, description="Ending aisle number."),
        from_dt: datetime = Query(
            default=None, description="Start shelved date to " "filter by."
        ),
        to_dt: datetime = Query(
            default=None, description="End shelved date to " "filter by."
        ),
    ):
        self.building_id = building_id
        self.module_id = module_id
        self.owner_id = owner_id
        self.aisle_num_from = aisle_num_from
        self.aisle_num_to = aisle_num_to
        self.from_dt = from_dt
        self.to_dt = to_dt


class UserJobItemsCountParams:
    """
    Query params for User Job Items Count Report.
    """

    def __init__(
        self,
        user_id: list[int] = Query(
            default=None, description="ID of the user to filter jobs."
        ),
        from_dt: datetime = Query(
            default=None, description="Start created date to " "filter by."
        ),
        to_dt: datetime = Query(
            default=None, description="End created date to " "filter by."
        ),
    ):
        self.user_id = user_id
        self.from_dt = from_dt
        self.to_dt = to_dt


class VerificationChangesParams:
    def __init__(
        self,
        workflow_id: list[int] = Query(
            default=None, description="ID of the workflow to filter jobs."
        ),
        completed_by_id: list[int] = Query(
            default=None, description="ID of the user to filter jobs."
        ),
        from_dt: datetime = Query(
            default=None, description="Start created date to " "filter by."
        ),
        to_dt: datetime = Query(
            default=None, description="End created date to " "filter by."
        ),
    ):
        self.workflow_id = workflow_id
        self.completed_by_id = completed_by_id
        self.from_dt = from_dt
        self.to_dt = to_dt


class RetrievalCountParams:
    def __init__(
        self,
        owner_id: list[int] = Query(
            default=None, description="ID of the user to filter jobs."
        ),
        from_dt: datetime = Query(
            default=None, description="Start created date to " "filter by."
        ),
        to_dt: datetime = Query(
            default=None, description="End created date to " "filter by."
        ),
    ):
        self.owner_id = owner_id
        self.from_dt = from_dt
        self.to_dt = to_dt


class BatchUploadParams:
    """
    Query params for Batch Upload Report.
    """
    def __init__(
        self,
        status: list[str] = Query(
            default=None, description="Status of the batch upload."
        ),
        user_id: list[int] = Query(
            default=None, description="ID of the user to filter batch uploads."
        ),
        withdraw_job_id: int = Query(
            default=None, description="ID of the withdraw job to filter batch uploads."
        ),
        file_name: str = Query(
            default=None, description="Name of the file to filter batch uploads."
        ),
        file_type: list[str] = Query(
            default=None, description="Type of the file to filter batch uploads."
        )
    ):
        self.status = status
        self.user_id = user_id
        self.withdraw_job_id = withdraw_job_id
        self.file_name = file_name
        self.file_type = file_type


class MoveDiscrepancyParams:
    def __init__(
        self,
        assigned_user_id: list[int] = Query(default=None, description="ID of the user to filter jobs."),
        owner_id: list[int] = Query(
            default=None, description="ID of the user to filter jobs."
        ),
        size_class_id: list[int] = Query(
            default=None, description="ID of the size class to filter jobs."
        ),
        container_type_id: list[int] = Query(
            default=None, description="ID of the container type to filter jobs."
        ),
        from_dt: datetime = Query(
            default=None, description="Start created date to " "filter by."
        ),
        to_dt: datetime = Query(
            default=None, description="End created date to " "filter by."
        ),
    ):
        self.assigned_user_id = assigned_user_id
        self.owner_id = owner_id
        self.size_class_id = size_class_id
        self.container_type_id = container_type_id
        self.from_dt = from_dt
        self.to_dt = to_dt
