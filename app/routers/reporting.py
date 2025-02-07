import csv
from io import StringIO
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.sql import exists
from sqlalchemy import func, union_all, literal, and_, or_, asc, distinct, desc, case
from sqlmodel import Session, select

from app.database.session import get_session
from app.logger import inventory_logger
from app.filter_params import (
    SortParams,
    ShelvingJobDiscrepancyParams,
    OpenLocationParams,
    AccessionedItemsParams,
    AisleItemsCountParams,
    NonTrayItemsCountParams,
    TrayItemCountParams,
    UserJobItemsCountParams,
    VerificationChangesParams,
    RetrievalCountParams
)
from app.models.accession_jobs import AccessionJob
from app.models.aisle_numbers import AisleNumber
from app.models.barcodes import Barcode
from app.models.item_withdrawals import ItemWithdrawal
from app.models.items import Item
from app.models.media_types import MediaType
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.non_tray_items import NonTrayItem
from app.models.owners import Owner
from app.models.pick_lists import PickList
from app.models.refile_items import RefileItem
from app.models.refile_jobs import RefileJob
from app.models.refile_non_tray_items import RefileNonTrayItem
from app.models.requests import Request
from app.models.shelving_jobs import ShelvingJob
from app.models.size_class import SizeClass
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.shelf_types import ShelfType
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.models.buildings import Building
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.modules import Module
from app.models.ladders import Ladder
from app.models.trays import Tray
from app.models.users import User
from app.models.verification_changes import VerificationChange
from app.models.verification_jobs import VerificationJob
from app.models.withdraw_jobs import WithdrawJob
from app.models.item_retrieval_events import ItemRetrievalEvent
from app.models.non_tray_item_retrieval_events import NonTrayItemRetrievalEvent
from app.schemas.reporting import (
    AccessionItemsDetailOutput,
    ShelvingJobDiscrepancyOutput,
    OpenLocationsOutput,
    AisleDetailReportItemCountOutput,
    NonTrayItemCountReadOutput,
    TrayItemCountReadOutput,
    UserJobItemCountReadOutput,
    VerificationChangesOutput,
    RetrievalItemCountReadOutput,
)
from app.config.exceptions import (
    NotFound,
    BadRequest,
    InternalServerError
)

router = APIRouter(
    prefix="/reporting",
    tags=["reporting"],
)


def get_accessioned_items_count_query(params):
    item_query_conditions = []
    non_tray_item_query_conditions = []
    selection = []
    group_by = []

    if params.owner_id:
        item_query_conditions.append(Item.owner_id.in_(params.owner_id))
        non_tray_item_query_conditions.append(NonTrayItem.owner_id.in_(params.owner_id))
    if params.size_class_id:
        item_query_conditions.append(Item.size_class_id.in_(params.size_class_id))
        non_tray_item_query_conditions.append(
            NonTrayItem.size_class_id.in_(params.size_class_id)
        )
    if params.media_type_id:
        item_query_conditions.append(Item.media_type_id.in_(params.media_type_id))
        non_tray_item_query_conditions.append(
            NonTrayItem.media_type_id.in_(params.media_type_id)
        )
    if params.from_dt:
        item_query_conditions.append(Item.accession_dt >= params.from_dt)
        non_tray_item_query_conditions.append(
            NonTrayItem.accession_dt >= params.from_dt
        )
    if params.to_dt:
        item_query_conditions.append(Item.accession_dt <= params.to_dt)
        non_tray_item_query_conditions.append(NonTrayItem.accession_dt <= params.to_dt)

    item_query = (
        select(
            Item.id.label("item_id"),
            Owner.name.label("owner_name"),
            SizeClass.name.label("size_class_name"),
            MediaType.name.label("media_type_name"),
        )
        .select_from(Item)
        .join(Owner, Owner.id == Item.owner_id)
        .join(SizeClass, SizeClass.id == Item.size_class_id)
        .join(MediaType, MediaType.id == Item.media_type_id)
        .filter(and_(*item_query_conditions))
    )
    non_tray_item_query = (
        select(
            NonTrayItem.id.label("item_id"),
            Owner.name.label("owner_name"),
            SizeClass.name.label("size_class_name"),
            MediaType.name.label("media_type_name"),
        )
        .select_from(NonTrayItem)
        .join(Owner, Owner.id == NonTrayItem.owner_id)
        .join(SizeClass, SizeClass.id == NonTrayItem.size_class_id)
        .join(MediaType, MediaType.id == NonTrayItem.media_type_id)
        .filter(and_(*non_tray_item_query_conditions))
    )

    combined_query = union_all(item_query, non_tray_item_query).subquery()

    if params.owner_id:
        selection.append(combined_query.c.owner_name)
        group_by.append(combined_query.c.owner_name)
    else:
        selection.append(literal("All").label("owner_name"))
    if params.size_class_id:
        selection.append(combined_query.c.size_class_name)
        group_by.append(combined_query.c.size_class_name)
    else:
        selection.append(literal("All").label("size_class_name"))
    if params.media_type_id:
        selection.append(combined_query.c.media_type_name)
        group_by.append(combined_query.c.media_type_name)
    else:
        selection.append(literal("All").label("media_type_name"))

    final_query = select(
        *selection,
        func.count().label("count"),
    ).select_from(combined_query)

    if group_by:
        final_query = final_query.group_by(*group_by)

    return final_query


@router.get("/accession-items/", response_model=Page[AccessionItemsDetailOutput])
def get_accessioned_items_count(
    session: Session = Depends(get_session),
    params: AccessionedItemsParams = Depends(),
):

    try:
        return paginate(session, get_accessioned_items_count_query(params))

    except Exception as e:
        inventory_logger.error(e)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


@router.get("/accession-items/download", response_class=StreamingResponse)
def get_accessioned_items_csv(
    session: Session = Depends(get_session),
    params: AccessionedItemsParams = Depends(),
):
    """
    Translates list response of AccessionedItems objects to csv,
    returns binary for download

    **Args**:
    - params: Accessioned Items Params: The parameters for the request.
        - owner_id: The list ID of the building.
        - size_class_id: The list ID of the size class.
        - media_type_id: The list ID of the media type
        - from_dt: The starting date.
        - to_dt: The ending date.

    **Returns**:
    - Streaming Response: The response with the csv file
    """
    # Get the query
    accession_query = get_accessioned_items_count_query(params)

    # Define the generator to stream data
    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)

        # Write header row
        writer.writerow(["owner_name", "size_class_name", "media_type_name", "count"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Write rows from query results
        for row in session.execute(accession_query):
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    # Return the StreamingResponse
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=accession_item_count.csv"
        },
    )


# SHELVING JOB DISCREPANCIES
@router.get(
    "/shelving-job-discrepancies/", response_model=Page[ShelvingJobDiscrepancyOutput]
)
def get_shelving_job_discrepancy_list(
    session: Session = Depends(get_session),
    params: ShelvingJobDiscrepancyParams = Depends(),
) -> list:
    """
    Returns a list of ShelvingJobDiscrepancy objects.
    """
    query = select(ShelvingJobDiscrepancy).distinct()
    if params.shelving_job_id:
        query = query.where(
            ShelvingJobDiscrepancy.shelving_job_id == params.shelving_job_id
        )
    if params.assigned_user_id:
        query = query.where(
            ShelvingJobDiscrepancy.assigned_user_id == params.assigned_user_id
        )
    if params.owner_id:
        query = query.where(ShelvingJobDiscrepancy.owner_id == params.owner_id)
    if params.size_class_id:
        query = query.where(
            ShelvingJobDiscrepancy.size_class_id == params.size_class_id
        )
    if params.from_dt:
        query = query.where(ShelvingJobDiscrepancy.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(ShelvingJobDiscrepancy.create_dt <= params.to_dt)

    return paginate(session, query)


@router.get("/shelving-job-discrepancies/download", response_class=StreamingResponse)
def get_shelving_job_report_csv(
    session: Session = Depends(get_session),
    params: ShelvingJobDiscrepancyParams = Depends(),
):
    """
    Translates list response of ShelvingJobDiscrepancy objects to csv,
    returns binary for download
    """
    query = select(ShelvingJobDiscrepancy).distinct()

    if params.shelving_job_id:
        query = query.where(
            ShelvingJobDiscrepancy.shelving_job_id == params.shelving_job_id
        )
    if params.assigned_user_id:
        query = query.where(
            ShelvingJobDiscrepancy.assigned_user_id == params.assigned_user_id
        )
    if params.owner_id:
        query = query.where(ShelvingJobDiscrepancy.owner_id == params.owner_id)
    if params.size_class_id:
        query = query.where(
            ShelvingJobDiscrepancy.size_class_id == params.size_class_id
        )
    if params.from_dt:
        query = query.where(ShelvingJobDiscrepancy.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(ShelvingJobDiscrepancy.create_dt <= params.to_dt)

    result = session.execute(query)
    rows = result.scalars().all()

    # Create an in-memory CSV
    output = StringIO()
    writer = csv.writer(output)

    # Write headers (optional: use column names dynamically)
    writer.writerow(
        [
            "discrepancy_id",
            "shelving_job_id",
            "tray",
            "non_tray_item",
            "assigned_user",
            "owner",
            "size_class",
            "assigned_location",
            "pre_assigned_location",
            "error",
            "create_dt",
            "update_dt",
        ]
    )

    tray_barcode_value = None
    non_tray_item_barcode_value = None
    assigned_user_name = None
    owner_name = None
    size_class_shortname = None

    # Write rows
    for row in rows:
        if row.non_tray_item:
            non_tray_item_barcode_value = row.non_tray_item.barcode.value
        if row.tray:
            tray_barcode_value = row.tray.barcode.value
        if row.assigned_user:
            assigned_user_name = row.assigned_user.name
        if row.owner:
            owner_name = row.owner.name
        if row.size_class:
            size_class_shortname = row.size_class.short_name
        writer.writerow(
            [
                row.id,
                row.shelving_job_id,
                tray_barcode_value,
                non_tray_item_barcode_value,
                assigned_user_name,
                owner_name,
                size_class_shortname,
                row.assigned_location,
                row.pre_assigned_location,
                row.error,
                row.create_dt,
                row.update_dt,
            ]
        )

    # Reset the buffer position
    output.seek(0)

    # Create a StreamingResponse
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=shelving_discrepancies.csv"
        },
    )


@router.get(
    "/shelving-job-discrepancies/{id}", response_model=ShelvingJobDiscrepancyOutput
)
def get_shelving_job_discrepancy_detail(
    id: int, session: Session = Depends(get_session)
):
    """
    Returns a single Shelving Job Discrepancy object
    """
    shelving_job_discrepancy = session.get(ShelvingJobDiscrepancy, id)

    if shelving_job_discrepancy:
        return shelving_job_discrepancy

    raise NotFound(detail=f"Shelving Job Discrepancy ID {id} Not Found")


# OPEN LOCATIONS REPORT
@router.get("/open-locations/", response_model=Page[OpenLocationsOutput])
def get_open_locations_list(
    session: Session = Depends(get_session), params: OpenLocationParams = Depends()
) -> list:
    """
    Returns a paginated list of shelf objects with
    unoccupied nested shelf positions based on search criteria
    """
    try:
        occupied_positions_cte = (
            select(
                ShelfPosition.shelf_id,
                func.count(ShelfPosition.id).label("occupied_positions"),
            )
            .where(
                (exists().where(ShelfPosition.id == Tray.shelf_position_id)) |
                (exists().where(ShelfPosition.id == NonTrayItem.shelf_position_id))
            )
            .group_by(ShelfPosition.shelf_id)
            .cte("occupied_positions_cte")
        )

        # Use CTE for total positions
        total_positions_cte = (
            select(
                ShelfPosition.shelf_id,
                func.count(ShelfPosition.id).label("total_positions"),
            )
            .group_by(ShelfPosition.shelf_id)
            .cte("total_positions_cte")
        )

        # Optimize joins using precomputed CTEs
        shelf_query = (
            select(Shelf)
            .distinct()
            .join(ShelfType, Shelf.shelf_type_id == ShelfType.id)
            .join(SizeClass, ShelfType.size_class_id == SizeClass.id)
            .join(Barcode, Shelf.barcode_id == Barcode.id)
            .join(Owner, Shelf.owner_id == Owner.id)
            .outerjoin(
                total_positions_cte,
                Shelf.id == total_positions_cte.c.shelf_id
            )
            .outerjoin(
                occupied_positions_cte,
                Shelf.id == occupied_positions_cte.c.shelf_id
            )
        )

        # Optimize filtering
        if not params.show_partial:
            shelf_query = shelf_query.where(
                func.coalesce(occupied_positions_cte.c.occupied_positions, 0) == 0
            )
        else:
            shelf_query = shelf_query.where(
                func.coalesce(occupied_positions_cte.c.occupied_positions, 0)
                < ShelfType.max_capacity
            )

        # Optimize owner filter with direct join
        if params.owner_id:
            shelf_query = shelf_query.filter(Owner.id.in_(params.owner_id))

        # Optimize location filtering
        if params.ladder_id:
            shelf_query = shelf_query.join(
                Ladder, Shelf.ladder_id == Ladder.id
            ).filter(Shelf.ladder_id == params.ladder_id)
        elif params.side_id:
            shelf_query = shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id).join(
                Side, Ladder.side_id == Side.id
            ).filter(Side.id == params.side_id)
        elif params.aisle_id:
            shelf_query = (
                shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id)
                .join(Side, Ladder.side_id == Side.id)
                .join(Aisle, Side.aisle_id == Aisle.id)
                .filter(Aisle.id == params.aisle_id)
            )
        elif params.module_id:
            shelf_query = (
                shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id)
                .join(Side, Ladder.side_id == Side.id)
                .join(Aisle, Side.aisle_id == Aisle.id)
                .join(Module, Aisle.module_id == Module.id)
                .filter(Module.id == params.module_id)
            )
        elif params.building_id:
            shelf_query = (
                shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id)
                .join(Side, Ladder.side_id == Side.id)
                .join(Aisle, Side.aisle_id == Aisle.id)
                .join(Module, Aisle.module_id == Module.id)
                .join(Building, Module.building_id == Building.id)
                .filter(Building.id == params.building_id)
            )

        return paginate(session, shelf_query)
    except Exception as e:
        inventory_logger.error(e)
        raise InternalServerError(detail=f"{e}")


@router.get("/open-locations/download", response_class=StreamingResponse)
def get_open_locations_csv(
    session: Session = Depends(get_session), params: OpenLocationParams = Depends()
):
    """
    Returns a csv report of shelf objects with
    unoccupied nested shelf positions based on search criteria
    """
    occupied_positions_cte = (
        select(
            ShelfPosition.shelf_id,
            func.count(ShelfPosition.id).label("occupied_positions"),
        )
        .where(
            (exists().where(ShelfPosition.id == Tray.shelf_position_id)) |
            (exists().where(ShelfPosition.id == NonTrayItem.shelf_position_id))
        )
        .group_by(ShelfPosition.shelf_id)
        .cte("occupied_positions_cte")
    )

    # Use CTE for total positions
    total_positions_cte = (
        select(
            ShelfPosition.shelf_id,
            func.count(ShelfPosition.id).label("total_positions"),
        )
        .group_by(ShelfPosition.shelf_id)
        .cte("total_positions_cte")
    )

    # Optimize joins using precomputed CTEs
    shelf_query = (
        select(Shelf)
        .distinct()
        .join(ShelfType, Shelf.shelf_type_id == ShelfType.id)
        .join(SizeClass, ShelfType.size_class_id == SizeClass.id)
        .join(Barcode, Shelf.barcode_id == Barcode.id)
        .join(Owner, Shelf.owner_id == Owner.id)
        .outerjoin(
            total_positions_cte,
            Shelf.id == total_positions_cte.c.shelf_id
        )
        .outerjoin(
            occupied_positions_cte,
            Shelf.id == occupied_positions_cte.c.shelf_id
        )
    )

    # Optimize filtering
    if not params.show_partial:
        shelf_query = shelf_query.where(
            func.coalesce(occupied_positions_cte.c.occupied_positions, 0) == 0
        )
    else:
        shelf_query = shelf_query.where(
            func.coalesce(occupied_positions_cte.c.occupied_positions, 0)
            < ShelfType.max_capacity
        )

    # Optimize owner filter with direct join
    if params.owner_id:
        shelf_query = shelf_query.filter(Owner.id.in_(params.owner_id))

    # Optimize location filtering
    if params.ladder_id:
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).filter(Shelf.ladder_id == params.ladder_id)
    elif params.side_id:
        shelf_query = shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id).join(
            Side, Ladder.side_id == Side.id
        ).filter(Side.id == params.side_id)
    elif params.aisle_id:
        shelf_query = (
            shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .filter(Aisle.id == params.aisle_id)
        )
    elif params.module_id:
        shelf_query = (
            shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .join(Module, Aisle.module_id == Module.id)
            .filter(Module.id == params.module_id)
        )
    elif params.building_id:
        shelf_query = (
            shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .join(Module, Aisle.module_id == Module.id)
            .join(Building, Module.building_id == Building.id)
            .filter(Building.id == params.building_id)
        )

    result = session.execute(shelf_query)
    rows = result.scalars().all()

    # Create an in-memory CSV
    output = StringIO()
    writer = csv.writer(output)

    # Write headers (optional: use column names dynamically)
    writer.writerow(
        [
            "shelf_barcode",
            "available_space",
            "location",
            "owner",
            "height",
            "width",
            "depth",
            "size_class",
        ]
    )

    # Write rows
    for row in rows:
        writer.writerow(
            [
                row.barcode.value,
                row.available_space,
                row.location,
                row.owner.name,
                row.height,
                row.width,
                row.depth,
                row.shelf_type.size_class.short_name,
            ]
        )

    # Reset the buffer position
    output.seek(0)

    # Create a StreamingResponse
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=open_locations.csv"},
    )


def get_aisle_item_counts_query(
    building_id: int, aisle_num_from: Optional[int], aisle_num_to: Optional[int]
):
    """
    Construct the query to fetch aisles with their associated counts.
    """
    query = (
        select(
            Aisle.id.label("aisle_id"),
            AisleNumber.number.label("aisle_number"),
            func.count(distinct(Shelf.id)).label("shelf_count"),
            func.count(distinct(Tray.id)).label("tray_count"),
            func.count(distinct(Item.id)).label("item_count"),
            func.count(distinct(NonTrayItem.id)).label("non_tray_item_count"),
        )
        .join(AisleNumber, Aisle.aisle_number_id == AisleNumber.id)
        .join(Module, Aisle.module_id == Module.id)
        .join(Side, Side.aisle_id == Aisle.id, isouter=True)
        .join(Ladder, Ladder.side_id == Side.id, isouter=True)
        .join(Shelf, Shelf.ladder_id == Ladder.id, isouter=True)
        .join(ShelfPosition, ShelfPosition.shelf_id == Shelf.id, isouter=True)
        .join(Tray, Tray.shelf_position_id == ShelfPosition.id, isouter=True)
        .join(Item, Item.tray_id == Tray.id, isouter=True)
        .join(
            NonTrayItem, NonTrayItem.shelf_position_id == ShelfPosition.id, isouter=True
        )
        .filter(Module.building_id == building_id)
        .order_by(asc(AisleNumber.number))
        .group_by(Aisle.id, AisleNumber.number)
    )

    if aisle_num_from is not None:
        query = query.filter(AisleNumber.number >= aisle_num_from)
    if aisle_num_to is not None:
        query = query.filter(AisleNumber.number <= aisle_num_to)

    return query


@router.get(
    "/aisles/items_count/",
    response_model=Page[AisleDetailReportItemCountOutput],
    response_description="List of item counts per aisle",
)
def get_aisle_items_count(
    session: Session = Depends(get_session), params: AisleItemsCountParams = Depends()
) -> list:
    """
    Get the total number of items in an aisle.

    **Args**:
    - params: Aisle Items Count Params: The parameters for the request.
        - building_id: The ID of the building.
        - aisle_num_from: The starting aisle number.
        - aisle_num_to: The ending aisle number.

    **Returns**:
    - Aisle Detail Report Item Count Output: The total number of items in the aisle.
    """
    # Validate building existence
    building = session.query(Building).filter(Building.id == params.building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    aisles_query = get_aisle_item_counts_query(
        params.building_id, params.aisle_num_from, params.aisle_num_to
    )

    # Paginate and transform results into the schema
    paginated_result = paginate(session, aisles_query)

    # Map results into the output schema
    paginated_result.items = [
        AisleDetailReportItemCountOutput(
            aisle_id=row.aisle_id,
            aisle_number=row.aisle_number,
            shelf_count=row.shelf_count,
            tray_count=row.tray_count,
            item_count=row.item_count,
            non_tray_item_count=row.non_tray_item_count,
            total_item_count=row.item_count + row.non_tray_item_count,
        )
        for row in paginated_result.items
    ]

    return paginated_result


@router.get("/aisles/items_count/download", response_class=StreamingResponse)
def get_aisles_items_count_csv(
    session: Session = Depends(get_session),
    params: AisleItemsCountParams = Depends(),
):
    """
    Download the total number of items in an aisle.

    **Args**:
    - params: Aisle Items Count Params: The parameters for the request.
        - building_id: The ID of the building.
        - aisle_num_from: The starting aisle number.
        - aisle_num_to: The ending aisle number.

    **Returns**:
    - The total number of items in the aisle.
    """
    # Validate building existence
    building = session.query(Building).filter(Building.id == params.building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    aisles_query = get_aisle_item_counts_query(
        params.building_id, params.aisle_num_from, params.aisle_num_to
    )

    # Define the generator to stream data
    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)
        # Write header row
        writer.writerow(
            [
                "aisle_number",
                "shelf_count",
                "tray_count",
                "item_count",
                "non_tray_item_count",
                "total_item_count",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Fetch results and write each row
        for row in session.execute(aisles_query):
            aisle_number = row.aisle_number
            shelf_count = row.shelf_count
            tray_count = row.tray_count
            item_count = row.item_count
            non_tray_item_count = row.non_tray_item_count
            total_item_count = item_count + non_tray_item_count

            writer.writerow(
                [
                    aisle_number,
                    shelf_count,
                    tray_count,
                    item_count,
                    non_tray_item_count,
                    total_item_count,
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    # Return the streaming response
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aisles_item_count.csv"},
    )


def get_non_tray_item_counts_query(params):
    """
    Construct the query to fetch non tray items with their associated counts as well
    as size class id, size class name, and size class short name.
    """
    # Base query to calculate the count
    query = (
        select(
            func.count(NonTrayItem.id).label("non_tray_item_count"),
            SizeClass.id.label("size_class_id"),
            SizeClass.name.label("size_class_name"),
            SizeClass.short_name.label("size_class_short_name"),
        )
        .join(ShelfPosition, ShelfPosition.id == NonTrayItem.shelf_position_id)
        .join(Shelf, Shelf.id == ShelfPosition.shelf_id)
        .join(Ladder, Ladder.id == Shelf.ladder_id)
        .join(Side, Side.id == Ladder.side_id)
        .join(Aisle, Aisle.id == Side.aisle_id)
        .join(AisleNumber, Aisle.aisle_number_id == AisleNumber.id)
        .join(SizeClass, NonTrayItem.size_class_id == SizeClass.id)
        .join(Module, Module.id == Aisle.module_id)
        .where(Module.building_id == params.building_id)
        .order_by(asc(SizeClass.id))
        .group_by(SizeClass.id)
    )

    # Apply filters
    if params.module_id:
        query = query.where(Module.id == params.module_id)
    if params.owner_id:
        query = query.where(NonTrayItem.owner_id.in_(params.owner_id))
    if params.size_class_id:
        query = query.where(NonTrayItem.size_class_id.in_(params.size_class_id))
    if params.aisle_num_from is not None:
        query = query.where(AisleNumber.number >= params.aisle_num_from)
    if params.aisle_num_to is not None:
        query = query.where(AisleNumber.number <= params.aisle_num_to)
    if params.from_dt:
        query = query.where(NonTrayItem.shelved_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(NonTrayItem.shelved_dt <= params.to_dt)

    if not params.from_dt or not params.to_dt:
        query = query.where(NonTrayItem.shelved_dt != None)

    # Execute the query and fetch the result
    return query


@router.get("/non_tray_items/count/", response_model=Page[NonTrayItemCountReadOutput])
def get_non_tray_item_count(
    session: Session = Depends(get_session), params: NonTrayItemsCountParams = Depends()
) -> list:
    """
    Get the total number of non tray items in an aisle.

    **Args**:
    - params: Non Tray Items Count Params: The parameters for the request.
        - building_id: ID of the building to filter aisles.
        - owner_id: ID of the owner to filter by.
        - size_class_id: ID of the size class to filter by.
        - aisle_num_from: Starting aisle number.
        - aisle_num_to: Ending aisle number.
        - from_dt: Start Accession date to filter by.
        - to_dt: End Accession date to filter by.

    **Returns**:
    - Non Tray Item Count Read Output: The total number of non tray items.
    """
    # Ensure the building exists
    building = session.get(Building, params.building_id)
    if not building:
        raise NotFound(detail="Building not found")

    # Ensure the modules exists (if module_id is provided)
    if params.module_id:
        modules = session.get(Module, params.module_id)
        if not modules:
            raise NotFound(detail="Module not found")

    # Ensure the size class exists (if size_class_id is provided)
    if params.size_class_id:
        size_classes = (
            session.query(SizeClass)
            .filter(SizeClass.id.in_(params.size_class_id))
            .all()
        )
        if not size_classes:
            raise NotFound(detail="Size class not found")

    return paginate(session, get_non_tray_item_counts_query(params))


@router.get("/non_tray_items/count/download", response_class=StreamingResponse)
def get_non_tray_item_count_csv(
    session: Session = Depends(get_session),
    params: NonTrayItemsCountParams = Depends(),
):
    """
      Download  the count of non-tray items in the building.

      **Parameters**:
      - params: Non Tray Items Count Params: The parameters for the request.
          - building_id: ID of the building to filter aisles.
          - owner_id: ID of the owner to filter by.
          - size_class_id: ID of the size class to filter by.
          - aisle_num_from: Starting aisle number.
          - aisle_num_to: Ending aisle number.
          - from_dt: Start Accession date to filter by.
          - to_dt: End Accession date to filter by.

      **Returns**:
    - Non Tray Item Count Read Output: The total number of non tray items.
    """
    # Ensure the building exists
    building = session.get(Building, params.building_id)
    if not building:
        raise NotFound(detail="Building not found")

    # Ensure the modules exists (if module_id is provided)
    if params.module_id:
        modules = session.get(Module, params.module_id)
        if not modules:
            raise NotFound(detail="Module not found")

    # Ensure the size class exists (if size_class_id is provided)
    if params.size_class_id:
        size_classes = (
            session.query(SizeClass)
            .filter(SizeClass.id.in_(params.size_class_id))
            .all()
        )
        if not size_classes:
            raise NotFound(detail="Size class not found")

    query = get_non_tray_item_counts_query(params)

    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)
        # Write header row
        writer.writerow(
            [
                "size_class_id",
                "size_class_name",
                "size_class_short_name",
                "non_tray_item_count",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in session.execute(query):
            size_class_id = row.size_class_id
            size_class_name = row.size_class_name
            size_class_short_nam = row.size_class_short_name
            non_tray_item_count = row.non_tray_item_count

            writer.writerow(
                [
                    size_class_id,
                    size_class_name,
                    size_class_short_nam,
                    non_tray_item_count,
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=non_tray_item_count.csv"},
    )


def get_tray_item_counts_query(params):
    """
    Construct the query to fetch non tray items with their associated counts as well
    as size class id, size class name, and size class short name.
    """
    # Base query to calculate the count
    query = (
        select(
            func.count(distinct(Tray.id)).label("tray_count"),
            func.count(distinct(Item.id)).label("tray_item_count"),
            SizeClass.id.label("size_class_id"),
            SizeClass.name.label("size_class_name"),
            SizeClass.short_name.label("size_class_short_name"),
        )
        .join(Tray, Tray.id == Item.tray_id)
        .join(ShelfPosition, ShelfPosition.id == Tray.shelf_position_id)
        .join(Shelf, Shelf.id == ShelfPosition.shelf_id)
        .join(Ladder, Ladder.id == Shelf.ladder_id)
        .join(Side, Side.id == Ladder.side_id)
        .join(Aisle, Aisle.id == Side.aisle_id)
        .join(AisleNumber, Aisle.aisle_number_id == AisleNumber.id)
        .join(SizeClass, Tray.size_class_id == SizeClass.id)
        .join(Module, Module.id == Aisle.module_id)
        .where(Module.building_id == params.building_id)
        .order_by(asc(SizeClass.id))
        .group_by(SizeClass.id)
    )

    # Apply filters
    if params.owner_id:
        query = query.where(Tray.owner_id.in_(params.owner_id))
    if params.module_id:
        query = query.where(Module.id == params.module_id)
    if params.aisle_num_from is not None:
        query = query.where(AisleNumber.number >= params.aisle_num_from)
    if params.aisle_num_to is not None:
        query = query.where(AisleNumber.number <= params.aisle_num_to)
    if params.from_dt:
        query = query.where(Tray.shelved_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(Tray.shelved_dt <= params.to_dt)

    if not params.from_dt or not params.to_dt:
        query = query.where(Tray.shelved_dt != None)

    # Execute the query and fetch the result
    return query


@router.get("/tray_items/count/", response_model=Page[TrayItemCountReadOutput])
def get_tray_item_count(
    session: Session = Depends(get_session), params: TrayItemCountParams = Depends()
) -> list:
    """
    Get the total number of tray items in an aisle.

    **Args**:
    - params: Tray Items Count Params: The parameters for the request.
        - building_id: ID of the building to filter aisles.
        - owner_id: ID of the owner to filter by.
        - aisle_num_from: Starting aisle number.
        - aisle_num_to: Ending aisle number.
        - from_dt: Start Accession date to filter by.
        - to_dt: End Accession date to filter by.

    **Returns**:
    - Tray Item Count Read Output: The total number of tray items.
    """
    # Ensure the building exists
    building = session.get(Building, params.building_id)
    if not building:
        raise NotFound(detail="Building not found")

    # Ensure the modules exists (if module_id is provided)
    if params.module_id:
        modules = session.get(Module, params.module_id)
        if not modules:
            raise NotFound(detail="Module not found")

    # Ensure the owners exists (if owner_id is provided)
    if params.owner_id:
        owners = session.query(Owner).filter(Owner.id.in_(params.owner_id)).all()
        if not owners:
            raise NotFound(detail="Owners not found")

    return paginate(session, get_tray_item_counts_query(params))


@router.get("/tray_items/count/download", response_class=StreamingResponse)
def get_tray_item_count_csv(
    session: Session = Depends(get_session),
    params: TrayItemCountParams = Depends(),
):
    """
      Download the count of tray items in the building.

      **Parameters**:
      - params: Tray Items Count Params: The parameters for the request.
          - building_id: ID of the building to filter aisles.
          - owner_id: ID of the owner to filter by.
          - aisle_num_from: Starting aisle number.
          - aisle_num_to: Ending aisle number.
          - from_dt: Start Accession date to filter by.
          - to_dt: End Accession date to filter by.

      **Returns**:
    - Tray Item Count Read Output: The total number of tray items.
    """
    # Ensure the building exists
    building = session.get(Building, params.building_id)
    if not building:
        raise NotFound(detail="Building not found")

    # Ensure the modules exists (if module_id is provided)
    if params.module_id:
        modules = session.get(Module, params.module_id)
        if not modules:
            raise NotFound(detail="Module not found")

    # Ensure the owners exists (if owner_id is provided)
    if params.owner_id:
        owners = session.query(Owner).filter(Owner.id.in_(params.owner_id)).all()
        if not owners:
            raise NotFound(detail="Owners not found")

    query = get_tray_item_counts_query(params)

    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)
        # Write header row
        writer.writerow(
            [
                "size_class_id",
                "size_class_name",
                "size_class_short_name",
                "tray_count",
                "tray_item_count",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in session.execute(query):
            size_class_id = row.size_class_id
            size_class_name = row.size_class_name
            size_class_short_name = row.size_class_short_name
            tray_count = row.tray_count
            tray_item_count = row.tray_item_count

            writer.writerow(
                [
                    size_class_id,
                    size_class_name,
                    size_class_short_name,
                    tray_count,
                    tray_item_count,
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tray_item_count.csv"},
    )


def accession_job_summary_query(params):
    selection = [literal("Accession Job").label("job_type")]
    conditions = [AccessionJob.status == "Completed"]
    group_by = []

    # Apply filters for user and date range
    if params.user_id:
        selection.append(User.id.label("user_id"))
        selection.append(
            func.concat(
                User.first_name.label("first_name"),
                literal(" "),
                User.last_name.label("last_name"),
            ).label("user_name")
        )
        conditions.append(User.id.in_(params.user_id))
        group_by.append(User.id)
    if params.from_dt:
        conditions.append(AccessionJob.create_dt >= params.from_dt)
    if params.to_dt:
        conditions.append(AccessionJob.create_dt <= params.to_dt)

    items_query = (
        select(
            *selection,
            func.count(Item.id).label("item_count"),
        )
        .select_from(Item)
        .join(AccessionJob, AccessionJob.id == Item.accession_job_id)
        .join(User, User.id == AccessionJob.user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )
    non_tray_item_query = (
        select(
            *selection,
            func.count(NonTrayItem.id).label("item_count"),
        )
        .select_from(NonTrayItem)
        .join(AccessionJob, AccessionJob.id == NonTrayItem.accession_job_id)
        .join(User, User.id == AccessionJob.user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )

    final_query = union_all(items_query, non_tray_item_query)

    return final_query


def verification_job_summary_query(params):
    selection = [literal("Verification Job").label("job_type")]
    conditions = [VerificationJob.status == "Completed"]
    group_by = []

    # Apply filters for user and date range
    if params.user_id:
        selection.append(User.id.label("user_id"))
        selection.append(
            func.concat(
                User.first_name.label("first_name"),
                literal(" "),
                User.last_name.label("last_name"),
            ).label("user_name")
        )
        conditions.append(User.id.in_(params.user_id))
        group_by.append(User.id)
    if params.from_dt:
        conditions.append(VerificationJob.create_dt >= params.from_dt)
    if params.to_dt:
        conditions.append(VerificationJob.create_dt <= params.to_dt)

    items_query = (
        select(
            *selection,
            func.count(Item.id).label("item_count"),
        )
        .select_from(Item)
        .join(VerificationJob, VerificationJob.id == Item.verification_job_id)
        .join(User, User.id == VerificationJob.user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )
    non_tray_items_query = (
        select(
            *selection,
            func.count(NonTrayItem.id).label("item_count"),
        )
        .select_from(NonTrayItem)
        .join(VerificationJob, VerificationJob.id == NonTrayItem.verification_job_id)
        .join(User, User.id == VerificationJob.user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )

    final_query = union_all(items_query, non_tray_items_query)

    return final_query


def shelving_job_summary_query(params):
    # Add a separate query for ShelvingJob
    selection = [literal("Shelving Job").label("job_type")]
    conditions = [ShelvingJob.status == "Completed"]
    group_by = []

    # Apply filters for user and date range
    if params.user_id:
        selection.append(User.id.label("user_id"))
        selection.append(
            func.concat(
                User.first_name.label("first_name"),
                literal(" "),
                User.last_name.label("last_name"),
            ).label("user_name")
        )
        conditions.append(User.id.in_(params.user_id))
        group_by.append(User.id)
    if params.from_dt:
        conditions.append(ShelvingJob.create_dt >= params.from_dt)
    if params.to_dt:
        conditions.append(ShelvingJob.create_dt <= params.to_dt)

    items_query = (
        select(
            *selection,
            func.count(distinct(Item.id)).label("item_count"),
        )
        .select_from(Item)
        .join(Tray, Tray.id == Item.tray_id)
        .join(ShelvingJob, ShelvingJob.id == Tray.shelving_job_id)
        .join(User, User.id == ShelvingJob.user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )

    non_tray_items_query = (
        select(
            *selection,
            func.count(distinct(NonTrayItem.id)).label("item_count"),
        )
        .select_from(NonTrayItem)
        .join(ShelvingJob, ShelvingJob.id == NonTrayItem.shelving_job_id)
        .join(User, User.id == ShelvingJob.user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )

    final_query = union_all(items_query, non_tray_items_query)

    return final_query


def picklist_summary_query(params):
    # Add a separate query for PickList
    selection = [literal("Pick List").label("job_type")]
    conditions = [PickList.status == "Completed"]
    group_by = []

    if params.user_id:
        selection.append(User.id.label("user_id"))
        selection.append(
            func.concat(
                User.first_name.label("first_name"),
                literal(" "),
                User.last_name.label("last_name"),
            ).label("user_name")
        )
        conditions.append(User.id.in_(params.user_id))
        group_by.append(User.id)
    if params.from_dt:
        conditions.append(PickList.create_dt >= params.from_dt)
    if params.to_dt:
        conditions.append(PickList.create_dt <= params.to_dt)

    query = (
        select(
            *selection,
            func.count(Request.id).label("item_count"),
        )
        .select_from(Request)
        .join(PickList, PickList.id == Request.pick_list_id)
        .join(User, User.id == PickList.user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )

    return query


def refile_job_summary_query(params):
    # Add a separate query for RefileJob
    selection = [literal("Refile Job").label("job_type")]
    conditions = [RefileJob.status == "Completed"]
    group_by = []

    if params.user_id:
        selection.append(User.id.label("user_id"))
        selection.append(
            func.concat(
                User.first_name.label("first_name"),
                literal(" "),
                User.last_name.label("last_name"),
            ).label("user_name")
        )
        conditions.append(User.id.in_(params.user_id))
        group_by.append(User.id)
    if params.from_dt:
        conditions.append(RefileJob.create_dt >= params.from_dt)
    if params.to_dt:
        conditions.append(RefileJob.create_dt <= params.to_dt)

    items_query = (
        select(
            *selection,
            func.count(Item.id).label("item_count"),
        )
        .select_from(RefileItem)
        .join(RefileJob, RefileJob.id == RefileItem.refile_job_id)
        .join(Item, Item.id == RefileItem.item_id)
        .join(User, User.id == RefileJob.assigned_user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )

    non_tray_items_query = (
        select(*selection, func.count(NonTrayItem.id).label("item_count"))
        .select_from(RefileNonTrayItem)
        .join(RefileJob, RefileJob.id == RefileNonTrayItem.refile_job_id)
        .join(NonTrayItem, NonTrayItem.id == RefileNonTrayItem.non_tray_item_id)
        .join(User, User.id == RefileJob.assigned_user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )

    final_query = union_all(items_query, non_tray_items_query)

    return final_query


def withdrawal_job_summary_query(params):
    # Add a separate query for WithdrawalJob
    selection = [literal("Withdraw Job").label("job_type")]
    conditions = [WithdrawJob.status == "Completed"]
    group_by = []

    if params.user_id:
        selection.append(User.id.label("user_id"))
        selection.append(
            func.concat(
                User.first_name.label("first_name"),
                literal(" "),
                User.last_name.label("last_name"),
            ).label("user_name")
        )
        conditions.append(User.id.in_(params.user_id))
        group_by.append(User.id)
    if params.from_dt:
        conditions.append(WithdrawJob.create_dt >= params.from_dt)
    if params.to_dt:
        conditions.append(WithdrawJob.create_dt <= params.to_dt)

    items_query = (
        select(*selection, func.count(Item.id).label("item_count"))
        .select_from(ItemWithdrawal)
        .join(WithdrawJob, WithdrawJob.id == ItemWithdrawal.withdraw_job_id)
        .join(Item, Item.id == ItemWithdrawal.item_id)
        .join(User, User.id == WithdrawJob.assigned_user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )

    non_tray_items_query = (
        select(*selection, func.count(NonTrayItem.id).label("item_count"))
        .select_from(NonTrayItemWithdrawal)
        .join(WithdrawJob, WithdrawJob.id == NonTrayItemWithdrawal.withdraw_job_id)
        .join(NonTrayItem, NonTrayItem.id == NonTrayItemWithdrawal.non_tray_item_id)
        .join(User, User.id == WithdrawJob.assigned_user_id)
        .where(and_(*conditions))
        .group_by(*group_by)
    )

    final_query = union_all(items_query, non_tray_items_query)

    return final_query


def get_user_job_summary_query(params, sort_params=None):
    job_queries = []

    # Add a separate query for AccessionJob
    accession_query = accession_job_summary_query(params)
    job_queries.append(accession_query)

    # Add a separate query for VerificationJob
    verification_query = verification_job_summary_query(params)
    job_queries.append(verification_query)

    # Add a separate query for ShelvingJob
    shelving_query = shelving_job_summary_query(params)
    job_queries.append(shelving_query)

    picklist_query = picklist_summary_query(params)
    job_queries.append(picklist_query)

    refile_query = refile_job_summary_query(params)
    job_queries.append(refile_query)

    withdrawal_query = withdrawal_job_summary_query(params)
    job_queries.append(withdrawal_query)

    # Combine all job queries using `union_all`
    combined_query = union_all(*job_queries).subquery()

    # Aggregate final results grouped by job_type
    selection = [
        combined_query.c.job_type,
        func.sum(combined_query.c.item_count).label("total_items_processed"),
    ]
    group_by = []
    order_by = []

    if sort_params is not None and sort_params.sort_by:
        if sort_params.sort_order not in ["asc", "desc"]:
            raise BadRequest(
                detail=f"Invalid value for ‘sort_order'. Allowed values are: ‘asc’, ‘desc’",
            )

        if sort_params.sort_by == "user_name":
            selection.append(combined_query.c.user_name)
            group_by.append(combined_query.c.user_id)
            group_by.append(combined_query.c.user_name)
            if sort_params.sort_order == "asc":
                order_by.append(asc(combined_query.c.user_name))
            else:
                order_by.append(desc(combined_query.c.user_name))
        if sort_params.sort_by == "job_type":
            if sort_params.sort_order == "asc":
                order_by.append(asc(combined_query.c.job_type))
            else:
                order_by.append(desc(combined_query.c.job_type))
        if sort_params.sort_by == "total_items_processed":
            if sort_params.sort_order == "asc":
                order_by.append(asc(combined_query.c.total_items_processed))
            else:
                order_by.append(desc(combined_query.c.total_items_processed))

    if params.user_id:
        selection.append(combined_query.c.user_name)
        group_by.append(combined_query.c.job_type)
        group_by.append(combined_query.c.user_name)
        order_by.append(combined_query.c.user_name)
    else:
        selection.append(selection.append(literal("All").label("user_name")))
        group_by.append(combined_query.c.job_type)
        order_by.append(combined_query.c.job_type)

    final_query = select(*selection).group_by(*group_by).order_by(*order_by)

    return final_query


@router.get("/user-jobs/count/", response_model=Page[UserJobItemCountReadOutput])
def get_user_job_summary(
    session: Session = Depends(get_session),
    params: UserJobItemsCountParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:

    if params.user_id:
        user = session.query(User).filter(User.id.in_(params.user_id)).all()
        if not user:
            raise NotFound(detail="User not found")

    query = get_user_job_summary_query(params, sort_params)

    return paginate(session, query)


@router.get("/user-jobs/count/download", response_class=StreamingResponse)
def get_user_job_summary_csv(
    session: Session = Depends(get_session), params: UserJobItemsCountParams = Depends()
):
    query = get_user_job_summary_query(params)

    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)
        # Write header row
        writer.writerow(["user_name", "job_type", "total_items_processed"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in session.execute(query):
            user_name = row.user_name
            job_type = row.job_type
            total_items_processed = row.total_items_processed

            writer.writerow([user_name, job_type, total_items_processed])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=user_job_count.csv"},
    )


def get_verification_change_query(params, sort_params=None):
    conditions = [VerificationJob.status == "Completed"]
    order_by = []

    if params.workflow_id:
        conditions.append(VerificationChange.workflow_id.in_(params.workflow_id))
    if params.completed_by_id:
        conditions.append(VerificationChange.completed_by_id.in_(params.completed_by_id))
    if params.from_dt:
        conditions.append(VerificationJob.update_dt >= params.from_dt)
    if params.to_dt:
        conditions.append(VerificationJob.update_dt <= params.to_dt)

    if sort_params is not None and sort_params.sort_by:
        if sort_params.sort_order not in ["asc", "desc"]:
            raise BadRequest(
                detail=f"Invalid value for ‘sort_order'. Allowed values are: ‘asc’, ‘desc’",
            )

        if sort_params.sort_by == "workflow_id":
            if sort_params.sort_order == "asc":
                order_by.append(asc(VerificationChange.workflow_id))
            else:
                order_by.append(desc(VerificationChange.workflow_id))
        if sort_params.sort_by == "completed_dt":
            if sort_params.sort_order == "asc":
                order_by.append(asc(VerificationJob.update_dt))
            else:
                order_by.append(desc(VerificationJob.update_dt))
        if sort_params.sort_by == "completed_by":
            if sort_params.sort_order == "asc":
                order_by.append(asc(VerificationChange.completed_by_id))
            else:
                order_by.append(desc(VerificationChange.completed_by_id))
        if (sort_params.sort_by == "item_barcode"):
            if sort_params.sort_order == "asc":
                order_by.append(asc(VerificationChange.item_barcode_value))
            else:
                order_by.append(desc(VerificationChange.item_barcode_value))
        if sort_params.sort_by == "tray_barcode":
            if sort_params.sort_order == "asc":
                order_by.append(asc(VerificationChange.tray_barcode_value))
            else:
                order_by.append(desc(VerificationChange.tray_barcode_value))
        if sort_params.sort_by == "action":
            if sort_params.sort_order == "asc":
                order_by.append(asc(VerificationChange.change_type))
            else:
                order_by.append(desc(VerificationChange.change_type))

    query = (
        select(
            VerificationChange.workflow_id,
            VerificationChange.item_barcode_value.label("item_barcode"),
            VerificationChange.tray_barcode_value.label("tray_barcode"),
            VerificationJob.update_dt.label("completed_dt"),
            func.concat(User.first_name, literal(" "), User.last_name).label(
                "completed_by"
            ),
            VerificationChange.change_type.label("action"),
        )
        .select_from(VerificationChange)
        .join(VerificationJob, VerificationJob.workflow_id == VerificationChange.workflow_id)
        .join(User, User.id == VerificationChange.completed_by_id)
        .where(and_(*conditions))
        .order_by(*order_by)
    )

    return query


@router.get("/verification-changes/summary/", response_model=Page[VerificationChangesOutput])
def get_verification_change_summary(
    session: Session = Depends(get_session),
    params: VerificationChangesParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Returns a list of VerificationChanges objects.
    """
    if params.workflow_id:
        job_workflow = session.query(VerificationJob).filter(
            VerificationJob.workflow_id.in_(params.workflow_id)).all()
        if not job_workflow:
            raise NotFound(detail="Verification Job(s) with workflow id(s) not found")
    if params.completed_by_id:
        user = session.query(User).filter(User.id.in_(params.completed_by_id)).all()
        if not user:
            raise NotFound(detail="User(s) not found")

    query = get_verification_change_query(params, sort_params)
    inventory_logger.info(f"get_verification_change_summary: {query}")
    query = query.subquery()

    return paginate(session, select(query))


@router.get("/verification-changes/summary/download", response_class=StreamingResponse)
def get_verification_change_summary_csv(
    session: Session = Depends(get_session), params: VerificationChangesParams = Depends()
):
    query = get_verification_change_query(params)
    query = query.subquery()

    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)
        # Write header row
        writer.writerow(
            [
                "workflow_id",
                "item_barcode",
                "tray_barcode",
                "completed_dt",
                "completed_by",
                "action",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        for row in session.execute(select(query)):
            workflow_id = row.workflow_id
            item_barcode = row.item_barcode if row.item_barcode else None
            tray_barcode = row.tray_barcode if row.tray_barcode else None
            completed_dt = row.completed_dt
            completed_by = row.completed_by
            action = row.action

            writer.writerow(
                [workflow_id, item_barcode, tray_barcode, completed_dt,
                 completed_by, action]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=verification_change_summary.csv"},
    )


def get_retrieval_item_count_query(params, sort_params=None):
    item_conditions = []
    non_tray_item_conditions = []
    order_by = []
    group_by = [Owner.name]

    if params.owner_id:
        item_conditions.append(ItemRetrievalEvent.owner_id.in_(params.owner_id))
        non_tray_item_conditions.append(
            NonTrayItemRetrievalEvent.owner_id.in_(params.owner_id)
            )
    if params.from_dt:
        item_conditions.append(ItemRetrievalEvent.create_dt >= params.from_dt)
        non_tray_item_conditions.append(
            NonTrayItemRetrievalEvent.create_dt >= params.from_dt
            )
    if params.to_dt:
        item_conditions.append(ItemRetrievalEvent.create_dt <= params.to_dt)
        non_tray_item_conditions.append(
            NonTrayItemRetrievalEvent.create_dt <= params.to_dt
            )


    # Query for ItemRetrievalEvent
    item_retrieved_query = (
        select(
            Owner.name.label("owner_name"),
            func.count(distinct(ItemRetrievalEvent.item_id)).label(
                "total_item_retrieved_count"
                ),
            func.count(ItemRetrievalEvent.item_id).label(
                "max_retrieved_count"
                ),
        )
        .select_from(ItemRetrievalEvent)
        .join(Owner, Owner.id == ItemRetrievalEvent.owner_id)
        .where(and_(*item_conditions))
        .group_by(*group_by, ItemRetrievalEvent.owner_id, ItemRetrievalEvent.item_id)
    )

    # Query for NonTrayItemRetrievalEvent
    non_tray_item_retrieved_query = (
        select(
            Owner.name.label("owner_name"),
            func.count(distinct(NonTrayItemRetrievalEvent.non_tray_item_id)).label(
                "total_item_retrieved_count"
                ),
            func.count(NonTrayItemRetrievalEvent.non_tray_item_id).label("max_retrieved_count")
        )
        .select_from(NonTrayItemRetrievalEvent)
        .join(Owner, Owner.id == NonTrayItemRetrievalEvent.owner_id)
        .where(and_(*non_tray_item_conditions))
        .group_by(*group_by, NonTrayItemRetrievalEvent.owner_id,
                  NonTrayItemRetrievalEvent.non_tray_item_id)
    )

    # Combine both queries using union_all
    combined_query = union_all(
        item_retrieved_query, non_tray_item_retrieved_query
    ).subquery()

    # Sorting logic
    if sort_params:
        if sort_params.sort_by == "owner_name":
            order_by.append(
                asc(
                    combined_query.c.owner_name
                    ) if sort_params.sort_order == "asc" else desc(
                    combined_query.c.owner_name
                    )
            )
        elif sort_params.sort_by == "total_item_retrieved_count":
            order_by.append(
                asc(
                    func.sum(combined_query.c.total_item_retrieved_count)
                    ) if sort_params.sort_order == "asc" else desc(
                    func.sum(combined_query.c.total_item_retrieved_count)
                    )
            )
        elif sort_params.sort_by == "max_retrieved_count":
            order_by.append(
                asc(
                    func.max(combined_query.c.max_retrieved_count)
                    ) if sort_params.sort_order == "asc" else desc(
                    func.max(combined_query.c.max_retrieved_count)
                    )
            )

    # Aggregate results to sum up total retrievals and get the maximum retrieval count per owner
    final_aggregation_query = (
        select(
            combined_query.c.owner_name,
            func.sum(combined_query.c.total_item_retrieved_count).label(
                "total_item_retrieved_count"
                ),
            func.max(combined_query.c.max_retrieved_count).label("max_retrieved_count"),
        )
        .group_by(combined_query.c.owner_name)
        .order_by(*order_by)
    )

    return final_aggregation_query


@router.get("/retrievals/count/", response_model=Page[RetrievalItemCountReadOutput])
def get_retrieval_count(
    session: Session = Depends(get_session),
    params: RetrievalCountParams = Depends(),
    sort_params: SortParams = Depends()
):
    """
    The count of items retrieved.

    **Parameters**:
    - params: Retrieval Count Params: The parameters for the request.
        - owner_id: ID of the owner to filter by.
        - from_dt: Start Accession date to filter by.
        - to_dt: End Accession date to filter by.

    **Returns**:
    - Retrieval Count Read Output: The total number of retrievals.
    """
    query = get_retrieval_item_count_query(params, sort_params)

    return paginate(session, query)


@router.get("/retrievals/count/download", response_class=StreamingResponse)
def get_retrieval_count_csv(
    session: Session = Depends(get_session), params: RetrievalCountParams = Depends()
):
    query = get_retrieval_item_count_query(params)

    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)
        # Write header row
        writer.writerow(["owner_name", "total_item_retrieved_count", "max_retrieved_count"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        for row in session.execute(query):
            owner_name = row.owner_name
            total_item_retrieved_count = row.total_item_retrieved_count
            max_retrieved_count = row.max_retrieved_count

            writer.writerow([owner_name, total_item_retrieved_count, max_retrieved_count])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=retrieval_count.csv"},
        )
