# /code/app/routers/reporting.py - FULL REFACRORED TO SQLALCHEMY V2

import csv
import gzip
import os
from io import StringIO, BytesIO

import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session, aliased # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, func, union_all, literal, and_, asc, desc, distinct, case, cast, BigInteger
from sqlalchemy.types import String
from app.models.side_orientations import SideOrientation
from starlette.responses import StreamingResponse, FileResponse
from starlette.background import BackgroundTask

from app.database.session import get_session
from app.logger import inventory_logger
from app.config.exceptions import NotFound, BadRequest, InternalServerError
from app.helpers.owner_helpers import get_owner_with_descendants
from app.sorting import (
    RetrievalItemCountSorter,
    ShelvingJobDiscrepancySorter,
    MoveDiscrepancySorter,
    OpenLocationsSorter,
    AisleItemsCountSorter,
    NonTrayItemCountSorter,
    TrayItemCountSorter,
    VerificationChangeSorter,
)
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
    MoveDiscrepancyOutput,
    ScheduledExportCreate,
    ScheduledExportRead,
    ExportHistoryRead
)

# --- ALL MODELS (Alphabetical for Mapper Health) ---
from app.models.accession_jobs import AccessionJob
from app.models.aisles import Aisle
from app.models.barcodes import Barcode
from app.models.batch_upload import BatchUpload
from app.models.buildings import Building
from app.models.container_types import ContainerType
from app.models.conveyance_bins import ConveyanceBin
from app.models.delivery_locations import DeliveryLocation
from app.models.ils_configurations import ILSConfiguration
from app.models.item_retrieval_events import ItemRetrievalEvent
from app.models.item_withdrawals import ItemWithdrawal
from app.models.items import Item
from app.models.ladders import Ladder
from app.models.media_types import MediaType
from app.models.modules import Module
from app.models.move_discrepancies import MoveDiscrepancy
from app.models.non_tray_item_retrieval_events import NonTrayItemRetrievalEvent
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.non_tray_items import NonTrayItem
from app.models.owner_delivery_locations import OwnerDeliveryLocation
from app.models.owner_tiers import OwnerTier
from app.models.owners import Owner
from app.models.pick_lists import PickList
from app.models.refile_items import RefileItem
from app.models.refile_jobs import RefileJob
from app.models.refile_non_tray_items import RefileNonTrayItem
from app.models.requests import Request
from app.models.shipping_bins import ShippingBin
from app.models.shipping_jobs import ShippingJob
# --- ALL MODELS (Trigger SQLAlchemy Mapper Initialization) ---
from app.models.all import *
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
    RetrievalCountParams,
    MoveDiscrepancyParams,
    VerificationReportParams,
    WithdrawnItemsReportParams,
    ShippingBinsReportParams,
    WorkerEfficiencyParams,
    InventoryHotZoneParams,
    CapacityForecastParams,
)
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
    MoveDiscrepancyOutput,
    VerificationStatusReportOutput,
    WithdrawnItemsReportOutput,
    ShippingBinsReportOutput,
    WorkerEfficiencyOutput,
    InventoryHotZoneOutput,
    CapacityForecastOutput,
    CapacityForecastHeightOutput,
    DailyPulseOutput,
)
from app.models.items import ItemStatus
from app.models.non_tray_items import NonTrayItemStatus

from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/reporting",
    tags=["reporting"],
    dependencies=[Depends(RequiresPermission("can_access_reports"))],
)


def get_accessioned_items_count_query(params, sort_params=None):
    item_query_conditions = []
    item_query_group_by = []
    non_tray_item_query_conditions = []
    non_tray_item_group_by = []
    include_month = bool(
        params.from_dt or params.to_dt
    )  # Enable month aggregation if needed

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

    if include_month:
        item_query_group_by.extend(
            [Item.accession_dt, func.extract("year", Item.accession_dt)]
        )
        non_tray_item_group_by.extend(
            [NonTrayItem.accession_dt, func.extract("year", NonTrayItem.accession_dt)]
        )

    # Base item query
    item_query = (
        select(
            func.count(Item.id).label("count"),
            (
                func.to_char(Item.accession_dt, "Mon").label("month")
                if include_month
                else literal(None).label("month")
            ),
            (
                func.extract("year", Item.accession_dt).label("year")
                if include_month
                else literal(None).label("year")
            ),
            Owner.name.label("owner_name"),
            SizeClass.name.label("size_class_name"),
            MediaType.name.label("media_type_name"),
        )
        .select_from(Item)
        .join(Owner, Owner.id == Item.owner_id)
        .join(SizeClass, SizeClass.id == Item.size_class_id)
        .join(MediaType, MediaType.id == Item.media_type_id)
        .filter(and_(*item_query_conditions))
        .group_by(Owner.name, SizeClass.name, MediaType.name, *item_query_group_by)
    )

    # Base non-tray item query
    non_tray_item_query = (
        select(
            func.count(NonTrayItem.id).label("count"),
            (
                func.to_char(NonTrayItem.accession_dt, "Mon").label("month")
                if include_month
                else literal(None).label("month")
            ),
            (
                func.extract("year", NonTrayItem.accession_dt).label("year")
                if include_month
                else literal(None).label("year")
            ),
            Owner.name.label("owner_name"),
            SizeClass.name.label("size_class_name"),
            MediaType.name.label("media_type_name"),
        )
        .select_from(NonTrayItem)
        .join(Owner, Owner.id == NonTrayItem.owner_id)
        .join(SizeClass, SizeClass.id == NonTrayItem.size_class_id)
        .join(MediaType, MediaType.id == NonTrayItem.media_type_id)
        .filter(and_(*non_tray_item_query_conditions))
        .group_by(Owner.name, SizeClass.name, MediaType.name, *non_tray_item_group_by)
    )

    # Combine item and non-tray queries
    combined_query = union_all(item_query, non_tray_item_query).subquery()
    selection = []
    group_by = []
    # Retain original selection and grouping
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

    # Add month breakdown if applicable
    if include_month:
        selection.extend(
            [combined_query.c.month, func.cast(combined_query.c.year, String)]
        )
        group_by.extend([combined_query.c.month, combined_query.c.year])
    else:
        selection.append(literal("All").label("month"))
        selection.append(literal("All").label("year"))

    # Aggregate count
    selection.append(func.coalesce(func.sum(combined_query.c.count), 0).label("count"))

    final_query = select(*selection).select_from(combined_query)

    if sort_params is not None and sort_params.sort_by:
        if sort_params.sort_order not in ["asc", "desc"]:
            raise BadRequest(
                detail="Invalid value for 'sort_order'. Allowed values are: 'asc', 'desc'"
            )

        order_func = asc if sort_params.sort_order == "asc" else desc

        if sort_params.sort_by == "owner":
            final_query = final_query.order_by(order_func("owner_name"))
            group_by.append("owner_name")
        if sort_params.sort_by == "total_count":
            final_query = final_query.order_by(order_func("count"))

    if group_by:
        final_query = final_query.group_by(*group_by)

    return final_query


@router.get("/accession-items/", response_model=Page[AccessionItemsDetailOutput])
def get_accessioned_items_count(
    session: Session = Depends(get_session),
    params: AccessionedItemsParams = Depends(),
    sort_params: SortParams = Depends(),
):
    """
    The count of items that have been accessioned.
    """
    # Expand owner IDs to include descendants if include_sub_tiers is True
    if params.owner_id and params.include_sub_tiers:
        params.owner_id = get_owner_with_descendants(session, params.owner_id)

    query = get_accessioned_items_count_query(
        params, sort_params
    )

    return paginate(session, query)


@router.get("/accession-items/download", response_class=StreamingResponse)
def get_accessioned_items_csv(
    session: Session = Depends(get_session),
    params: AccessionedItemsParams = Depends(),
    sort_params: SortParams = Depends(),
):
    """
    Translates list response of AccessionedItems objects to csv,
    returns binary for download
    """

    accession_query = get_accessioned_items_count_query(params)

    # Define the generator to stream data
    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)

        # Write header row
        writer.writerow(
            [
                "year",
                "month",
                "owner_name",
                "size_class_name",
                "media_type_name",
                "count",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Write rows from query results
        # V2 FIX: session.execute(query) is correct, but needs a .all() call inside the loop's iterable
        for row in session.execute(accession_query).all():
            writer.writerow(
                [
                    row.year,
                    row.month,
                    row.owner_name,
                    row.size_class_name,
                    row.media_type_name,
                    row.count,
                ]
            )
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
    sort_params: SortParams = Depends(),
) -> list:
    """
    Returns a list of ShelvingJobDiscrepancy objects.
    """
    query = select(ShelvingJobDiscrepancy)

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

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = ShelvingJobDiscrepancySorter(ShelvingJobDiscrepancy)
        query = sorter.apply_sorting(query, sort_params)

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
    query = select(ShelvingJobDiscrepancy)

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

    # V2 FIX: session.execute(query) returns a Result object
    result = session.execute(query)
    # V2 FIX: .scalars().all() needed to get ORM objects
    rows = result.scalars().all()

    # Create an in-memory CSV
    output = StringIO()
    writer = csv.writer(output)
    # ... (rest of CSV generation logic is maintained) ...
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
    session: Session = Depends(get_session),
    params: OpenLocationParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Returns a paginated list of shelf objects with
    unoccupied nested shelf positions based on search criteria
    """
    # try:
    shelf_query = (
        select(Shelf)
        .join(ShelfType, Shelf.shelf_type_id == ShelfType.id)
        .join(SizeClass, ShelfType.size_class_id == SizeClass.id)
        .join(Barcode, Shelf.barcode_id == Barcode.id)
        .join(Owner, Shelf.owner_id == Owner.id)
        .filter(Shelf.available_space > 0)
    )

    # Optimize filtering
    if not params.show_partial:
        shelf_query = shelf_query.where(
            Shelf.available_space == ShelfType.max_capacity
        )
    else:
        shelf_query = shelf_query.where(
            Shelf.available_space <= ShelfType.max_capacity
        )

    # Expand owner IDs to include descendants if include_sub_tiers is True
    if params.owner_id and params.include_sub_tiers:
        params.owner_id = get_owner_with_descendants(session, params.owner_id)

    # Optimize owner filter with direct join
    if params.owner_id:
        shelf_query = shelf_query.filter(Owner.id.in_(params.owner_id))

    if params.size_class_id:
        shelf_query = shelf_query.filter(SizeClass.id.in_(params.size_class_id))

    # Search filter params for server-side filtering
    if params.location_search:
        shelf_query = shelf_query.filter(Shelf.location.ilike(f"%{params.location_search}%"))
    if params.shelf_barcode_search:
        shelf_query = shelf_query.filter(Barcode.value.ilike(f"%{params.shelf_barcode_search}%"))
    if params.owner_search:
        shelf_query = shelf_query.filter(Owner.name.ilike(f"%{params.owner_search}%"))
    if params.size_class_search:
        shelf_query = shelf_query.filter(SizeClass.short_name.ilike(f"%{params.size_class_search}%"))

    # Optimize location filtering
    if params.ladder_id:
        shelf_query = shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id).filter(
            Shelf.ladder_id == params.ladder_id
        )
    elif params.side_id:
        shelf_query = (
            shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .filter(Side.id == params.side_id)
        )
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

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = OpenLocationsSorter(Shelf)
        shelf_query = sorter.apply_sorting(shelf_query, sort_params)

    # CRITICAL FIX: Paginate now takes only the query object
    return paginate(session, shelf_query)
    # except Exception as e:
    #     inventory_logger.error(e)
    #     raise InternalServerError(detail=f"{e}")


@router.get("/open-locations/download", response_class=StreamingResponse)
def get_open_locations_csv(
    session: Session = Depends(get_session), params: OpenLocationParams = Depends()
):
    """
    Returns a csv report of shelf objects with
    unoccupied nested shelf positions based on search criteria
    """
    shelf_query = (
        select(Shelf)
        .join(ShelfType, Shelf.shelf_type_id == ShelfType.id)
        .join(SizeClass, ShelfType.size_class_id == SizeClass.id)
        .join(Barcode, Shelf.barcode_id == Barcode.id)
        .join(Owner, Shelf.owner_id == Owner.id)
        .filter(Shelf.available_space > 0)
    )

    # Optimize filtering
    if not params.show_partial:
        shelf_query = shelf_query.where(Shelf.available_space == ShelfType.max_capacity)
    else:
        shelf_query = shelf_query.where(Shelf.available_space <= ShelfType.max_capacity)

    # Optimize owner filter with direct join
    if params.owner_id:
        shelf_query = shelf_query.filter(Owner.id.in_(params.owner_id))

    if params.size_class_id:
        shelf_query = shelf_query.filter(SizeClass.id.in_(params.size_class_id))

    # Optimize location filtering
    if params.ladder_id:
        shelf_query = shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id).filter(
            Shelf.ladder_id == params.ladder_id
        )
    elif params.side_id:
        shelf_query = (
            shelf_query.join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .filter(Side.id == params.side_id)
        )
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
    # V2 FIX: .scalars().all() needed to get ORM objects
    rows = result.scalars().all()

    # Create an in-memory CSV
    output = StringIO()
    writer = csv.writer(output)
    # ... (rest of CSV generation logic is maintained) ...
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


def get_aisle_item_counts_query(params, sort_params=None):
    """
    Construct the query to fetch aisles with their associated counts.
    """
    query = (
        select(
            Aisle.id.label("aisle_id"),
            Aisle.aisle_number.label("aisle_number"),
            func.count(distinct(Shelf.id)).label("shelf_count"),
            func.count(distinct(Tray.id)).label("tray_count"),
            func.count(distinct(Item.id)).label("item_count"),
            func.count(distinct(NonTrayItem.id)).label("non_tray_item_count"),
            (
                func.count(distinct(Item.id)) + func.count(distinct(NonTrayItem.id))
            ).label("total_item_count"),
        )
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
        .filter(Module.building_id == params.building_id)
        .group_by(Aisle.id, Aisle.aisle_number)
    )

    if params.aisle_num_from is not None:
        query = query.filter(Aisle.aisle_number >= params.aisle_num_from)
    if params.aisle_num_to is not None:
        query = query.filter(Aisle.aisle_number <= params.aisle_num_to)

    # Validate and Apply sorting based on sort_params
    if sort_params is not None and sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = AisleItemsCountSorter(Aisle)
        query = sorter.apply_sorting(query, sort_params)
    else:
        # Apply default sorting
        query = query.order_by(asc(Aisle.aisle_number))

    return query


@router.get(
    "/aisles/items_count/",
    response_model=Page[AisleDetailReportItemCountOutput],
    response_description="List of item counts per aisle",
)
def get_aisle_items_count(
    session: Session = Depends(get_session),
    params: AisleItemsCountParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get the total number of items in an aisle.
    """
    # Validate building existence
    # V2 FIX: session.query().filter().first() -> session.get()
    building = session.get(Building, params.building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    aisles_query = get_aisle_item_counts_query(params, sort_params)

    # Paginate and transform results into the schema
    # CRITICAL FIX: Paginate now takes only the query object
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
            total_item_count=row.total_item_count,
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
    """
    # Validate building existence
    # V2 FIX: session.query().filter().first() -> session.get()
    building = session.get(Building, params.building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    aisles_query = get_aisle_item_counts_query(
        params
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
        # V2 FIX: session.execute(query) returns a Result object
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


def get_non_tray_item_counts_query(params, sort_params=None):
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
        .join(SizeClass, NonTrayItem.size_class_id == SizeClass.id)
        .join(Module, Module.id == Aisle.module_id)
        .where(Module.building_id == params.building_id)
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
        query = query.where(Aisle.aisle_number >= params.aisle_num_from)
    if params.aisle_num_to is not None:
        query = query.where(Aisle.aisle_number <= params.aisle_num_to)
    if params.from_dt:
        query = query.where(NonTrayItem.shelved_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(NonTrayItem.shelved_dt <= params.to_dt)

    if not params.from_dt or not params.to_dt:
        query = query.where(NonTrayItem.shelved_dt != None)

        # Validate and Apply sorting based on sort_params
    if sort_params is not None and sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = NonTrayItemCountSorter(NonTrayItem)
        query = sorter.apply_sorting(query, sort_params)
    else:
        query = query.order_by(asc(SizeClass.id))

    # Execute the query and fetch the result
    return query


@router.get("/non_tray_items/count/", response_model=Page[NonTrayItemCountReadOutput])
def get_non_tray_item_count(
    session: Session = Depends(get_session),
    params: NonTrayItemsCountParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get the total number of non tray items in an aisle.
    """
    # Ensure the building exists
    # V2 FIX: session.get()
    building = session.get(Building, params.building_id)
    if not building:
        raise NotFound(detail="Building not found")

    # Ensure the modules exists (if module_id is provided)
    if params.module_id:
        # V2 FIX: session.get()
        modules = session.get(Module, params.module_id)
        if not modules:
            raise NotFound(detail="Module not found")

    # Ensure the size class exists (if size_class_id is provided)
    if params.size_class_id:
        # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
        size_classes = (
            session.execute(select(SizeClass).filter(SizeClass.id.in_(params.size_class_id)))
            .scalars()
            .all()
        )
        if not size_classes:
            raise NotFound(detail="Size class not found")

    # Expand owner IDs to include descendants if include_sub_tiers is True
    if params.owner_id and params.include_sub_tiers:
        params.owner_id = get_owner_with_descendants(session, params.owner_id)

    # CRITICAL FIX: Paginate now takes only the query object
    return paginate(session, get_non_tray_item_counts_query(params, sort_params))


@router.get("/non_tray_items/count/download", response_class=StreamingResponse)
def get_non_tray_item_count_csv(
    session: Session = Depends(get_session),
    params: NonTrayItemsCountParams = Depends(),
):
    """
      Download  the count of non-tray items in the building.
    """
    # Ensure the building exists
    # V2 FIX: session.get()
    building = session.get(Building, params.building_id)
    if not building:
        raise NotFound(detail="Building not found")

    # Ensure the modules exists (if module_id is provided)
    if params.module_id:
        # V2 FIX: session.get()
        modules = session.get(Module, params.module_id)
        if not modules:
            raise NotFound(detail="Module not found")

    # Ensure the size class exists (if size_class_id is provided)
    if params.size_class_id:
        # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
        size_classes = (
            session.execute(select(SizeClass).filter(SizeClass.id.in_(params.size_class_id)))
            .scalars()
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

        for row in session.execute(query): # V2 EXECUTION
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


def get_tray_item_counts_query(params, sort_params=None):
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
        .join(SizeClass, Tray.size_class_id == SizeClass.id)
        .join(Module, Module.id == Aisle.module_id)
        .where(Module.building_id == params.building_id)
        .group_by(SizeClass.id)
    )

    # Apply filters
    if params.owner_id:
        query = query.where(Tray.owner_id.in_(params.owner_id))
    if params.module_id:
        query = query.where(Module.id == params.module_id)
    if params.aisle_num_from is not None:
        query = query.where(Aisle.aisle_number >= params.aisle_num_from)
    if params.aisle_num_to is not None:
        query = query.where(Aisle.aisle_number <= params.aisle_num_to)
    if params.from_dt:
        query = query.where(Tray.shelved_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(Tray.shelved_dt <= params.to_dt)

    if not params.from_dt or not params.to_dt:
        query = query.where(Tray.shelved_dt != None)

    if sort_params is not None and sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = TrayItemCountSorter(Tray)
        query = sorter.apply_sorting(query, sort_params)
    else:
        query = query.order_by(asc(SizeClass.id))
    # Execute the query and fetch the result
    return query


@router.get("/tray_items/count/", response_model=Page[TrayItemCountReadOutput])
def get_tray_item_count(
    session: Session = Depends(get_session),
    params: TrayItemCountParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Get the total number of tray items in an aisle.
    """
    # Ensure the building exists
    # V2 FIX: session.get()
    building = session.get(Building, params.building_id)
    if not building:
        raise NotFound(detail="Building not found")

    # Ensure the modules exists (if module_id is provided)
    if params.module_id:
        # V2 FIX: session.get()
        modules = session.get(Module, params.module_id)
        if not modules:
            raise NotFound(detail="Module not found")

    # Ensure the owners exists (if owner_id is provided)
    if params.owner_id:
        # Expand owner IDs to include descendants if include_sub_tiers is True
        if params.include_sub_tiers:
            params.owner_id = get_owner_with_descendants(session, params.owner_id)
        # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
        owners = session.execute(select(Owner).filter(Owner.id.in_(params.owner_id))).scalars().all()
        if not owners:
            raise NotFound(detail="Owners not found")

    # CRITICAL FIX: Paginate now takes only the query object
    return paginate(session, get_tray_item_counts_query(params, sort_params))


@router.get("/tray_items/count/download", response_class=StreamingResponse)
def get_tray_item_count_csv(
    session: Session = Depends(get_session),
    params: TrayItemCountParams = Depends(),
):
    """
      Download the count of tray items in the building.
    """
    # Ensure the building exists
    # V2 FIX: session.get()
    building = session.get(Building, params.building_id)
    if not building:
        raise NotFound(detail="Building not found")

    # Ensure the modules exists (if module_id is provided)
    if params.module_id:
        # V2 FIX: session.get()
        modules = session.get(Module, params.module_id)
        if not modules:
            raise NotFound(detail="Module not found")

    # Ensure the owners exists (if owner_id is provided)
    if params.owner_id:
        # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
        owners = session.execute(select(Owner).filter(Owner.id.in_(params.owner_id))).scalars().all()
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

        for row in session.execute(query): # V2 EXECUTION
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
        .join(User, User.id == AccessionJob.assigned_user_id)
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
        .join(User, User.id == AccessionJob.assigned_user_id)
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
        .join(User, User.id == VerificationJob.assigned_user_id)
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
        .join(User, User.id == VerificationJob.assigned_user_id)
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
        .join(User, User.id == ShelvingJob.assigned_user_id)
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
        .join(User, User.id == ShelvingJob.assigned_user_id)
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
        .join(User, User.id == PickList.assigned_user_id)
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

    # Apply filters
    group_by = [combined_query.c.job_type]
    if params.user_id:
        selection.append(combined_query.c.user_name)
        group_by.append(combined_query.c.user_name)
    else:
        selection.append(literal("All").label("user_name")) # FIXED: literal was being appended twice

    # Apply sorting
    order_by = []
    if sort_params is not None and sort_params.sort_by:
        if sort_params.sort_order not in ["asc", "desc"]:
            raise BadRequest(
                detail=f"Invalid value for ‘sort_order'. Allowed values are: ‘asc’, ‘desc’",
            )

        if sort_params.sort_by == "job_type":
            if sort_params.sort_order == "asc":
                order_by.append(asc(combined_query.c.job_type))
            else:
                order_by.append(desc(combined_query.c.job_type))
        if sort_params.sort_by == "total_items_processed":
            if sort_params.sort_order == "asc":
                order_by.append(asc(func.sum(combined_query.c.item_count)))
            else:
                order_by.append(desc(func.sum(combined_query.c.item_count)))

    final_query = select(*selection).group_by(*group_by).order_by(*order_by)

    # Search filter params for server-side filtering
    if params.user_name_search:
        final_query = final_query.where(combined_query.c.user_name.ilike(f"%{params.user_name_search}%"))
    if params.job_type_search:
        final_query = final_query.where(combined_query.c.job_type.ilike(f"%{params.job_type_search}%"))

    return final_query


@router.get("/user-jobs/count/", response_model=Page[UserJobItemCountReadOutput])
def get_user_job_summary(
    session: Session = Depends(get_session),
    params: UserJobItemsCountParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
    if params.user_id:
        user = session.execute(select(User).filter(User.id.in_(params.user_id))).scalars().all()
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

        for row in session.execute(query): # V2 EXECUTION
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
        conditions.append(
            VerificationChange.completed_by_id.in_(params.completed_by_id)
        )
    if params.from_dt:
        conditions.append(VerificationJob.update_dt >= params.from_dt)
    if params.to_dt:
        conditions.append(VerificationJob.update_dt <= params.to_dt)

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
        .join(
            VerificationJob,
            VerificationJob.workflow_id == VerificationChange.workflow_id,
        )
        .join(User, User.id == VerificationChange.completed_by_id)
        .where(and_(*conditions))
    )

    if sort_params is not None and sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = VerificationChangeSorter(VerificationChange)
        query = sorter.apply_sorting(query, sort_params)

    return query


@router.get(
    "/verification-changes/summary/", response_model=Page[VerificationChangesOutput]
)
def get_verification_change_summary(
    session: Session = Depends(get_session),
    params: VerificationChangesParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Returns a list of VerificationChanges objects.
    """
    if params.workflow_id:
        # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
        job_workflow = (
            session.execute(select(VerificationJob).filter(VerificationJob.workflow_id.in_(params.workflow_id)))
            .scalars()
            .all()
        )
        if not job_workflow:
            raise NotFound(detail="Verification Job(s) with workflow id(s) not found")
    if params.completed_by_id:
        # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
        user = session.execute(select(User).filter(User.id.in_(params.completed_by_id))).scalars().all()
        if not user:
            raise NotFound(detail="User(s) not found")

    query = get_verification_change_query(params, sort_params)
    query = query.subquery()

    # CRITICAL FIX: Paginate needs both session and query for SQLAlchemy 2.0
    return paginate(session, select(query))


@router.get("/verification-changes/summary/download", response_class=StreamingResponse)
def get_verification_change_summary_csv(
    session: Session = Depends(get_session),
    params: VerificationChangesParams = Depends(),
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
        for row in session.execute(select(query)): # V2 EXECUTION
            workflow_id = row.workflow_id
            item_barcode = row.item_barcode if row.item_barcode else None
            tray_barcode = row.tray_barcode if row.tray_barcode else None
            completed_dt = row.completed_dt
            completed_by = row.completed_by
            action = row.action

            writer.writerow(
                [
                    workflow_id,
                    item_barcode,
                    tray_barcode,
                    completed_dt,
                    completed_by,
                    action,
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=verification_change_summary.csv"
        },
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
            func.count(ItemRetrievalEvent.item_id).label("max_retrieved_count"),
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
            func.count(NonTrayItemRetrievalEvent.non_tray_item_id).label(
                "max_retrieved_count"
            ),
        )
        .select_from(NonTrayItemRetrievalEvent)
        .join(Owner, Owner.id == NonTrayItemRetrievalEvent.owner_id)
        .where(and_(*non_tray_item_conditions))
        .group_by(
            *group_by,
            NonTrayItemRetrievalEvent.owner_id,
            NonTrayItemRetrievalEvent.non_tray_item_id,
        )
    )

    # Combine both queries using union_all
    combined_query = union_all(
        item_retrieved_query, non_tray_item_retrieved_query
    ).subquery()

    # Aggregate results to sum up total retrievals and get the maximum retrieval count per owner
    final_aggregation_query = select(
        combined_query.c.owner_name,
        func.sum(combined_query.c.total_item_retrieved_count).label(
            "total_item_retrieved_count"
        ),
        func.max(combined_query.c.max_retrieved_count).label("max_retrieved_count"),
    ).group_by(combined_query.c.owner_name)

    # Sorting logic
    if sort_params is not None and sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = RetrievalItemCountSorter(ItemRetrievalEvent)
        final_aggregation_query = sorter.apply_sorting(
            final_aggregation_query, sort_params
        )

    return final_aggregation_query


@router.get("/retrievals/count/", response_model=Page[RetrievalItemCountReadOutput])
def get_retrieval_count(
    session: Session = Depends(get_session),
    params: RetrievalCountParams = Depends(),
    sort_params: SortParams = Depends(),
):
    """
    The count of items retrieved.
    """
    # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
    if params.owner_id:
        # Expand owner IDs to include descendants if include_sub_tiers is True
        if params.include_sub_tiers:
            params.owner_id = get_owner_with_descendants(session, params.owner_id)
        owner = session.execute(select(Owner).filter(Owner.id.in_(params.owner_id))).scalars().all()
        if not owner:
            raise NotFound(detail="Owner(s) not found")

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
        writer.writerow(
            ["owner_name", "total_item_retrieved_count", "max_retrieved_count"]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        for row in session.execute(query): # V2 EXECUTION
            owner_name = row.owner_name
            total_item_retrieved_count = row.total_item_retrieved_count
            max_retrieved_count = row.max_retrieved_count

            writer.writerow(
                [owner_name, total_item_retrieved_count, max_retrieved_count]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=retrieval_count.csv"},
    )


@router.get(
    "/move-discrepancies/", response_model=Page[MoveDiscrepancyOutput]
)
def get_move_discrepancy_list(
    session: Session = Depends(get_session),
    params: MoveDiscrepancyParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Returns a list of Move Discrepancy objects.
    """
    query = select(MoveDiscrepancy)

    if params.assigned_user_id:
        query = query.where(
            MoveDiscrepancy.assigned_user_id.in_(params.assigned_user_id)
        )
    if params.owner_id:
        query = query.where(MoveDiscrepancy.owner_id.in_(params.owner_id))
    if params.size_class_id:
        query = query.where(
            MoveDiscrepancy.size_class_id.in_(params.size_class_id)
        )
    if params.container_type_id:
        query = query.where(
            MoveDiscrepancy.container_type_id.in_(params.container_type_id)
        )
    if params.from_dt:
        query = query.where(MoveDiscrepancy.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(MoveDiscrepancy.create_dt <= params.to_dt)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = MoveDiscrepancySorter(MoveDiscrepancy)
        query = sorter.apply_sorting(query, sort_params)
    else:
        query = query.order_by(MoveDiscrepancy.create_dt.desc())

    return paginate(session, query)


@router.get("/move-discrepancies/download", response_class=StreamingResponse)
def get_move_report_csv(
    session: Session = Depends(get_session),
    params: MoveDiscrepancyParams = Depends(),
):
    """
    Translates list response of move Discrepancy objects to csv,
    returns binary for download
    """
    query = select(MoveDiscrepancy)

    if params.assigned_user_id:
        query = query.where(
            MoveDiscrepancy.assigned_user_id.in_(params.assigned_user_id)
        )
    if params.owner_id:
        query = query.where(MoveDiscrepancy.owner_id.in_(params.owner_id))
    if params.size_class_id:
        query = query.where(
            MoveDiscrepancy.size_class_id.in_(params.size_class_id)
        )
    if params.container_type_id:
        query = query.where(
            MoveDiscrepancy.container_type_id.in_(params.container_type_id)
        )
    if params.from_dt:
        query = query.where(MoveDiscrepancy.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(MoveDiscrepancy.create_dt <= params.to_dt)

    result = session.execute(query)
    # V2 FIX: .scalars().all() needed to get ORM objects
    rows = result.scalars().all()

    # Create an in-memory CSV
    output = StringIO()
    writer = csv.writer(output)

    # Write headers (optional: use column names dynamically)
    writer.writerow(
        [
            "discrepancy_id",
            "tray",
            "non_tray_item",
            "assigned_user",
            "owner",
            "size_class",
            "container_type",
            "original_assigned_location",
            "current_assigned_location",
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
    container_type_type = None

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
        if row.container_type:
            container_type_type = row.container_type.type
        writer.writerow(
            [
                row.id,
                tray_barcode_value,
                non_tray_item_barcode_value,
                assigned_user_name,
                owner_name,
                size_class_shortname,
                container_type_type,
                row.original_assigned_location,
                row.current_assigned_location,
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
            "Content-Disposition": "attachment; filename=move_discrepancies.csv"
        },
    )


def get_verification_status_query(params: VerificationReportParams):
    if params.container_type == "Tray":
        query = (
            select(
                Barcode.value.label("barcode"),
                Owner.name.label("owner"),
                VerificationJob.id.label("verification_job_id"),
                VerificationJob.update_dt.label("verification_dt"),
            )
            .select_from(Tray)
            .join(Item, Item.tray_id == Tray.id)
            .join(VerificationJob, Item.verification_job_id == VerificationJob.id)
            .join(Barcode, Tray.barcode_id == Barcode.id)
            .join(Owner, Tray.owner_id == Owner.id)
            .where(
                Item.status == ItemStatus.Verified,
                VerificationJob.status == "Completed",
            )
            .distinct(Tray.id)
        )
    else:
        # Non-Tray
        query = (
            select(
                Barcode.value.label("barcode"),
                Owner.name.label("owner"),
                VerificationJob.id.label("verification_job_id"),
                VerificationJob.update_dt.label("verification_dt"),
            )
            .select_from(NonTrayItem)
            .join(VerificationJob, NonTrayItem.verification_job_id == VerificationJob.id)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .join(Owner, NonTrayItem.owner_id == Owner.id)
            .where(
                NonTrayItem.status == NonTrayItemStatus.Verified,
                VerificationJob.status == "Completed",
            )
        )


    if params.from_dt:
        query = query.where(VerificationJob.update_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(VerificationJob.update_dt <= params.to_dt)

    # Search filter params for server-side filtering
    if params.barcode_search:
        query = query.where(Barcode.value.ilike(f"%{params.barcode_search}%"))
    if params.owner_search:
        query = query.where(Owner.name.ilike(f"%{params.owner_search}%"))

    return query


@router.get("/verification-status", response_model=Page[VerificationStatusReportOutput])
def get_verification_status_report(
    session: Session = Depends(get_session),
    params: VerificationReportParams = Depends(),
) -> list:
    """
    Get a paginated list of verification status items.
    """
    query = get_verification_status_query(params)
    return paginate(session, query)


@router.get("/verification-status/download", response_class=StreamingResponse)
def get_verification_status_download_csv(
    session: Session = Depends(get_session),
    params: VerificationReportParams = Depends(),
):
    query = get_verification_status_query(params)

    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)
        # Write header row
        writer.writerow(
            [
                "Barcode",
                "Owner",
                "Verification Job #",
                "Verification Date",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Execute query
        for row in session.execute(query):
            writer.writerow(
                [
                    row.barcode,
                    row.owner,
                    row.verification_job_id,
                    row.verification_dt,
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    # Create a StreamingResponse
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=verification_status.csv"
        },
    )


def get_withdrawn_items_query(params: WithdrawnItemsReportParams):
    """
    Build query for withdrawn items report.
    """
    # Alias for withdrawn barcode lookup
    WithdrawnBarcode = aliased(Barcode)
    WithdrawnBarcodeNonTray = aliased(Barcode)

    # Build Tray Items query
    tray_query = (
        select(
            WithdrawnBarcode.value.label("barcode"),
            Owner.name.label("owner"),
            Item.withdrawn_location.label("withdrawn_location"),
            Item.withdrawal_dt.label("withdrawal_dt"),
        )
        .select_from(Item)
        .outerjoin(WithdrawnBarcode, Item.withdrawn_barcode_id == WithdrawnBarcode.id)
        .outerjoin(Owner, Item.owner_id == Owner.id)
        .where(Item.status == ItemStatus.Withdrawn)
    )

    # Build Non-Tray Items query
    non_tray_query = (
        select(
            WithdrawnBarcodeNonTray.value.label("barcode"),
            Owner.name.label("owner"),
            NonTrayItem.withdrawn_location.label("withdrawn_location"),
            NonTrayItem.withdrawal_dt.label("withdrawal_dt"),
        )
        .select_from(NonTrayItem)
        .outerjoin(WithdrawnBarcodeNonTray, NonTrayItem.withdrawn_barcode_id == WithdrawnBarcodeNonTray.id)
        .outerjoin(Owner, NonTrayItem.owner_id == Owner.id)
        .where(NonTrayItem.status == NonTrayItemStatus.Withdrawn)
    )

    # Apply date filters to Tray query
    if params.from_dt:
        tray_query = tray_query.where(Item.withdrawal_dt >= params.from_dt)
    if params.to_dt:
        tray_query = tray_query.where(Item.withdrawal_dt <= params.to_dt)
    if params.owner_id:
        tray_query = tray_query.where(Item.owner_id.in_(params.owner_id))

    # Apply date filters to Non-Tray query
    if params.from_dt:
        non_tray_query = non_tray_query.where(NonTrayItem.withdrawal_dt >= params.from_dt)
    if params.to_dt:
        non_tray_query = non_tray_query.where(NonTrayItem.withdrawal_dt <= params.to_dt)
    if params.owner_id:
        non_tray_query = non_tray_query.where(NonTrayItem.owner_id.in_(params.owner_id))

    # Return based on container type
    if params.container_type == "Tray":
        return tray_query
    elif params.container_type == "Non-Tray":
        return non_tray_query
    else:
        # "All" or None - combine both queries using union_all
        # Create CTE to allow proper pagination
        combined_cte = union_all(tray_query, non_tray_query).cte("combined_withdrawn")
        return select(
            combined_cte.c.barcode,
            combined_cte.c.owner,
            combined_cte.c.withdrawn_location,
            combined_cte.c.withdrawal_dt
        )



@router.get("/withdrawn-items/", response_model=Page[WithdrawnItemsReportOutput])
def get_withdrawn_items_report(
    session: Session = Depends(get_session),
    params: WithdrawnItemsReportParams = Depends(),
) -> list:
    """
    Get a paginated list of withdrawn items.
    """
    # Expand owner IDs to include descendants if include_sub_tiers is True
    if params.owner_id and params.include_sub_tiers:
        params.owner_id = get_owner_with_descendants(session, params.owner_id)

    query = get_withdrawn_items_query(params)
    return paginate(session, query)


@router.get("/withdrawn-items/download", response_class=StreamingResponse)
def get_withdrawn_items_download_csv(
    session: Session = Depends(get_session),
    params: WithdrawnItemsReportParams = Depends(),
):
    """
    Download withdrawn items report as CSV.
    """
    query = get_withdrawn_items_query(params)

    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)
        # Write header row
        writer.writerow(
            [
                "Barcode",
                "Owner",
                "Last Location",
                "Withdrawal Date",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Execute query
        for row in session.execute(query):
            writer.writerow(
                [
                    row.barcode,
                    row.owner,
                    row.withdrawn_location,
                    row.withdrawal_dt,
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    # Create a StreamingResponse
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=withdrawn_items.csv"
        },
    )



@router.get("/shipping-bins/", response_model=Page[ShippingBinsReportOutput])
def get_shipping_bins_report(
    session: Session = Depends(get_session),
    params: ShippingBinsReportParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Returns a list of active (uncleared) shipping bins.
    """
    query = (
        select(ShippingBin)
        .join(ShippingJob, ShippingBin.shipping_job_id == ShippingJob.id)
        .outerjoin(DeliveryLocation, ShippingBin.delivery_location_id == DeliveryLocation.id)
        .where(ShippingBin.cleared_dt.is_(None))
    )

    if params.from_dt:
        query = query.where(ShippingJob.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(ShippingJob.create_dt <= params.to_dt)
    
    if params.delivery_location_id:
         query = query.where(ShippingBin.delivery_location_id.in_(params.delivery_location_id))

    # Basic sorting by created date desc if no sort param
    if not sort_params.sort_by:
        query = query.order_by(desc(ShippingJob.create_dt))
    else:
        # TODO: Implement ShippingBinSorter if needed, for now basic sorting support
        if sort_params.sort_by == "create_dt":
             order_func = asc if sort_params.sort_order == "asc" else desc
             query = query.order_by(order_func(ShippingJob.create_dt))
        elif sort_params.sort_by == "shipping_job_id":
             order_func = asc if sort_params.sort_order == "asc" else desc
             query = query.order_by(order_func(ShippingJob.id))
        elif sort_params.sort_by == "barcode":
             order_func = asc if sort_params.sort_order == "asc" else desc
             query = query.order_by(order_func(ShippingBin.barcode))
        elif sort_params.sort_by == "delivery_location":
             order_func = asc if sort_params.sort_order == "asc" else desc
             query = query.order_by(order_func(DeliveryLocation.name))
        elif sort_params.sort_by == "item_count":
             # This is a bit complex as item_count is a property or aggregation
             # For now, skip sorting by item count or handle in memory if pages are small (not recommended)
             pass


    # Enhance the result with item counts
    # Getting item counts might require a separate query or group by if not efficient
    # But current ShippingBin model has `items` relationship (lazy="selectin"), so it should be available on the objects.
    # The output schema expects `item_count`. We can add a property to the model or compute it here.
    # ShippingBinsReportOutput uses `from_attributes=True`, passing the ShippingBin object.
    # We need to make sure ShippingBin object has `item_count` attribute or key.
    
    # Let's inspect ShippingBin model again. It has `items` relationship.
    # We can add a property to ShippingBin model or wrap the result.
    
    return paginate(session, query)


@router.get("/shipping-bins/download", response_class=StreamingResponse)
def get_shipping_bins_csv(
    session: Session = Depends(get_session),
    params: ShippingBinsReportParams = Depends(),
):
    """
    Returns a csv report of active shipping bins.
    """
    query = (
        select(ShippingBin)
        .join(ShippingJob, ShippingBin.shipping_job_id == ShippingJob.id)
        .outerjoin(DeliveryLocation, ShippingBin.delivery_location_id == DeliveryLocation.id)
        .where(ShippingBin.cleared_dt.is_(None))
    )

    if params.from_dt:
        query = query.where(ShippingJob.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(ShippingJob.create_dt <= params.to_dt)
    if params.delivery_location_id:
         query = query.where(ShippingBin.delivery_location_id.in_(params.delivery_location_id))

    # Order by date
    query = query.order_by(desc(ShippingJob.create_dt))

    result = session.execute(query)
    rows = result.scalars().all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "bin_number",
            "shipping_job_number",
            "created_date",
            "item_count",
            "delivery_location",
        ]
    )

    for row in rows:
        writer.writerow(
            [
                row.barcode if row.barcode else "",
                row.shipping_job_id,
                row.shipping_job.create_dt,
                len(row.items),
                row.delivery_location.name if row.delivery_location else "",
            ]
        )

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shipping_bins.csv"},
    )


# --- FACILITY INTELLIGENCE REPORTS ---

def get_worker_efficiency_query(params):
    """
    Construct the query measuring worker throughput (Items/Hour) across all job types.
    """
    # Define subqueries for each job type to union them
    from app.models.trays import Tray
    from app.models.items import Item
    from app.models.non_tray_items import NonTrayItem
    from app.models.requests import Request

    # Pre-aggregating counts grouped by job_id to resolve SQL-level N+1 subqueries
    shelving_trays_subq = select(
        Tray.shelving_job_id.label("job_id"),
        func.count(Tray.id).label("tray_count")
    ).group_by(Tray.shelving_job_id).subquery()

    shelving_nontrays_subq = select(
        NonTrayItem.shelving_job_id.label("job_id"),
        func.count(NonTrayItem.id).label("nontray_count")
    ).group_by(NonTrayItem.shelving_job_id).subquery()

    accession_items_subq = select(
        Item.accession_job_id.label("job_id"),
        func.count(Item.id).label("item_count")
    ).group_by(Item.accession_job_id).subquery()

    accession_nontrays_subq = select(
        NonTrayItem.accession_job_id.label("job_id"),
        func.count(NonTrayItem.id).label("nontray_count")
    ).group_by(NonTrayItem.accession_job_id).subquery()

    picklist_requests_subq = select(
        Request.pick_list_id.label("job_id"),
        func.count(Request.id).label("request_count")
    ).group_by(Request.pick_list_id).subquery()

    verification_items_subq = select(
        Item.verification_job_id.label("job_id"),
        func.count(Item.id).label("item_count")
    ).group_by(Item.verification_job_id).subquery()

    verification_nontrays_subq = select(
        NonTrayItem.verification_job_id.label("job_id"),
        func.count(NonTrayItem.id).label("nontray_count")
    ).group_by(NonTrayItem.verification_job_id).subquery()

    # Build the main job queries with pre-aggregated counts joined
    shelving_subq = select(
        ShelvingJob.assigned_user_id.label("user_id"),
        ShelvingJob.run_time.label("run_time"),
        (
            func.coalesce(shelving_trays_subq.c.tray_count, 0) +
            func.coalesce(shelving_nontrays_subq.c.nontray_count, 0)
        ).label("items"),
        literal("Shelving").label("job_type")
    ).select_from(ShelvingJob)\
     .outerjoin(shelving_trays_subq, ShelvingJob.id == shelving_trays_subq.c.job_id)\
     .outerjoin(shelving_nontrays_subq, ShelvingJob.id == shelving_nontrays_subq.c.job_id)\
     .where(ShelvingJob.assigned_user_id != None)

    # Note: Tray count is removed from Accession total to avoid double counting
    accession_subq = select(
        AccessionJob.assigned_user_id.label("user_id"),
        AccessionJob.run_time.label("run_time"),
        (
            func.coalesce(accession_items_subq.c.item_count, 0) +
            func.coalesce(accession_nontrays_subq.c.nontray_count, 0)
        ).label("items"),
        literal("Accession").label("job_type")
    ).select_from(AccessionJob)\
     .outerjoin(accession_items_subq, AccessionJob.id == accession_items_subq.c.job_id)\
     .outerjoin(accession_nontrays_subq, AccessionJob.id == accession_nontrays_subq.c.job_id)\
     .where(AccessionJob.assigned_user_id != None)

    pick_list_subq = select(
        PickList.assigned_user_id.label("user_id"),
        PickList.run_time.label("run_time"),
        func.coalesce(picklist_requests_subq.c.request_count, 0).label("items"),
        literal("PickList").label("job_type")
    ).select_from(PickList)\
     .outerjoin(picklist_requests_subq, PickList.id == picklist_requests_subq.c.job_id)\
     .where(PickList.assigned_user_id != None)

    # Note: Tray count is removed from Verification total to avoid double counting
    verification_subq = select(
        VerificationJob.assigned_user_id.label("user_id"),
        VerificationJob.run_time.label("run_time"),
        (
            func.coalesce(verification_items_subq.c.item_count, 0) +
            func.coalesce(verification_nontrays_subq.c.nontray_count, 0)
        ).label("items"),
        literal("Verification").label("job_type")
    ).select_from(VerificationJob)\
     .outerjoin(verification_items_subq, VerificationJob.id == verification_items_subq.c.job_id)\
     .outerjoin(verification_nontrays_subq, VerificationJob.id == verification_nontrays_subq.c.job_id)\
     .where(VerificationJob.assigned_user_id != None)

    # Filter by user if provided
    if params.user_id:
        shelving_subq = shelving_subq.where(ShelvingJob.assigned_user_id.in_(params.user_id))
        accession_subq = accession_subq.where(AccessionJob.assigned_user_id.in_(params.user_id))
        pick_list_subq = pick_list_subq.where(PickList.assigned_user_id.in_(params.user_id))
        verification_subq = verification_subq.where(VerificationJob.assigned_user_id.in_(params.user_id))

    # Filter by date range if provided
    if params.from_dt:
        shelving_subq = shelving_subq.where(ShelvingJob.create_dt >= params.from_dt)
        accession_subq = accession_subq.where(AccessionJob.create_dt >= params.from_dt)
        pick_list_subq = pick_list_subq.where(PickList.create_dt >= params.from_dt)
        verification_subq = verification_subq.where(VerificationJob.create_dt >= params.from_dt)

    if params.to_dt:
        shelving_subq = shelving_subq.where(ShelvingJob.create_dt <= params.to_dt)
        accession_subq = accession_subq.where(AccessionJob.create_dt <= params.to_dt)
        pick_list_subq = pick_list_subq.where(PickList.create_dt <= params.to_dt)
        verification_subq = verification_subq.where(VerificationJob.create_dt <= params.to_dt)

    # Collect active subqueries based on job_type filter
    active_subqs = []
    if not params.job_type or "Shelving" in params.job_type:
        active_subqs.append(shelving_subq)
    if not params.job_type or "Accession" in params.job_type:
        active_subqs.append(accession_subq)
    if not params.job_type or "PickList" in params.job_type:
        active_subqs.append(pick_list_subq)
    if not params.job_type or "Verification" in params.job_type:
        active_subqs.append(verification_subq)

    if not active_subqs:
        # Fallback if filter excluded everything
        active_subqs = [shelving_subq, accession_subq, pick_list_subq, verification_subq]

    combined = union_all(*active_subqs).subquery()

    # Final aggregation query
    total_seconds = func.extract('epoch', func.sum(combined.c.run_time))
    items_per_hour = (func.sum(combined.c['items']) * 3600.0) / func.nullif(total_seconds, 0)

    query = (
        select(
            combined.c.user_id,
            func.concat(User.first_name, ' ', User.last_name).label("user_name"),
            combined.c.job_type,
            func.count().label("total_jobs"),
            func.sum(combined.c['items']).label("total_items_processed"),
            func.coalesce(
                func.to_char(func.sum(combined.c.run_time), 'HH24:MI:SS'), '00:00:00'
            ).label("total_active_time"),
            func.round(func.coalesce(items_per_hour, 0)).label("items_per_hour")
        )
        .join(User, User.id == combined.c.user_id)
        .group_by(combined.c.user_id, User.first_name, User.last_name, combined.c.job_type)
    )

    return query


@router.get("/worker-efficiency/", response_model=Page[WorkerEfficiencyOutput])
def get_worker_efficiency(
    session: Session = Depends(get_session),
    params: WorkerEfficiencyParams = Depends(),
):
    """
    SLA Report: Measures worker throughput (Items/Hour) across all job types.
    """
    query = get_worker_efficiency_query(params)

    return paginate(session, query)


@router.get("/worker-efficiency/download", response_class=StreamingResponse)
def get_worker_efficiency_csv(
    session: Session = Depends(get_session),
    params: WorkerEfficiencyParams = Depends(),
):
    """
    Translates list response of WorkerEfficiency rows to csv,
    returns binary for download
    """
    query = get_worker_efficiency_query(params)

    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "user_id",
                "user_name",
                "job_type",
                "total_jobs",
                "total_items_processed",
                "total_active_time",
                "items_per_hour",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in session.execute(query):
            writer.writerow(
                [
                    row.user_id,
                    row.user_name,
                    row.job_type,
                    row.total_jobs,
                    row.total_items_processed,
                    row.total_active_time,
                    row.items_per_hour,
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=worker_efficiency.csv"},
    )


def get_inventory_hot_zones_query(session, params):
    """
    Construct the query measuring retrieval frequency (heatmap) by building and aisle.
    """
    # 1. Tray Item Retrievals Subquery
    tray_retrievals_subq = (
        select(
            Building.name.label("building_name"),
            Aisle.aisle_number.label("aisle_number"),
            ItemRetrievalEvent.create_dt
        )
        .join(Item, ItemRetrievalEvent.item_id == Item.id)
        .join(Tray, Item.tray_id == Tray.id)
        .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id)
        .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
        .join(Ladder, Shelf.ladder_id == Ladder.id)
        .join(Side, Ladder.side_id == Side.id)
        .join(Aisle, Side.aisle_id == Aisle.id)
        .join(Module, Aisle.module_id == Module.id)
        .join(Building, Module.building_id == Building.id)
    )

    # 2. Non-Tray Item Retrievals Subquery
    non_tray_retrievals_subq = (
        select(
            Building.name.label("building_name"),
            Aisle.aisle_number.label("aisle_number"),
            NonTrayItemRetrievalEvent.create_dt
        )
        .join(NonTrayItem, NonTrayItemRetrievalEvent.non_tray_item_id == NonTrayItem.id)
        .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id)
        .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
        .join(Ladder, Shelf.ladder_id == Ladder.id)
        .join(Side, Ladder.side_id == Side.id)
        .join(Aisle, Side.aisle_id == Aisle.id)
        .join(Module, Aisle.module_id == Module.id)
        .join(Building, Module.building_id == Building.id)
    )

    # Apply filters to subqueries
    if params.building_id:
        tray_retrievals_subq = tray_retrievals_subq.where(Building.id == params.building_id)
        non_tray_retrievals_subq = non_tray_retrievals_subq.where(Building.id == params.building_id)
    if params.from_dt:
        tray_retrievals_subq = tray_retrievals_subq.where(ItemRetrievalEvent.create_dt >= params.from_dt)
        non_tray_retrievals_subq = non_tray_retrievals_subq.where(NonTrayItemRetrievalEvent.create_dt >= params.from_dt)
    if params.to_dt:
        tray_retrievals_subq = tray_retrievals_subq.where(ItemRetrievalEvent.create_dt <= params.to_dt)
        non_tray_retrievals_subq = non_tray_retrievals_subq.where(NonTrayItemRetrievalEvent.create_dt <= params.to_dt)

    combined_retrievals = union_all(tray_retrievals_subq, non_tray_retrievals_subq).subquery()
    
    # Calculate total for percentages
    total_count_query = select(func.count()).select_from(combined_retrievals)
    total_count = session.execute(total_count_query).scalar() or 1

    # Final aggregation
    query = (
        select(
            combined_retrievals.c.building_name,
            combined_retrievals.c.aisle_number,
            func.count().label("retrieval_count"),
            (func.count() * 100.0 / total_count).label("percent_of_total")
        )
        .group_by(combined_retrievals.c.building_name, combined_retrievals.c.aisle_number)
        .order_by(desc("retrieval_count"))
    )

    return query


@router.get("/hot-zones/", response_model=Page[InventoryHotZoneOutput])
def get_inventory_hot_zones(
    session: Session = Depends(get_session),
    params: InventoryHotZoneParams = Depends(),
):
    """
    Heatmap: Retrieval frequency by building and aisle.
    """
    query = get_inventory_hot_zones_query(session, params)

    return paginate(session, query)


@router.get("/hot-zones/download", response_class=StreamingResponse)
def get_inventory_hot_zones_csv(
    session: Session = Depends(get_session),
    params: InventoryHotZoneParams = Depends(),
):
    """
    Translates list response of InventoryHotZone rows to csv,
    returns binary for download
    """
    query = get_inventory_hot_zones_query(session, params)

    def generate_csv():
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "building_name",
                "aisle_number",
                "retrieval_count",
                "percent_of_total",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in session.execute(query):
            writer.writerow(
                [
                    row.building_name,
                    row.aisle_number,
                    row.retrieval_count,
                    row.percent_of_total,
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_hot_zones.csv"},
    )


@router.get("/capacity-forecast/", response_model=List[CapacityForecastOutput])
def get_capacity_forecast(
    session: Session = Depends(get_session),
    params: CapacityForecastParams = Depends(),
):
    """
    Predictive: Storage runway in months for each size class.
    """
    owner_ids = None
    if params.owner_id:
        if params.include_sub_owners:
            owner_ids = get_owner_with_descendants(session, params.owner_id)
        else:
            owner_ids = [params.owner_id]

    # 1. Current Available Space (Facility total or filtered by owner/building)
    space_stmt = (
        select(
            SizeClass.name.label("size_class_name"),
            func.sum(Shelf.available_space).label("current_available_space")
        )
        .join(ShelfType, Shelf.shelf_type_id == ShelfType.id)
        .join(SizeClass, ShelfType.size_class_id == SizeClass.id)
        .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)
        .join(Side, Ladder.side_id == Side.id, isouter=True)
        .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)
        .join(Module, Aisle.module_id == Module.id, isouter=True)
        .join(Building, Module.building_id == Building.id, isouter=True)
    )
    if params.building_id:
        space_stmt = space_stmt.where(Building.id == params.building_id)
    if owner_ids:
        space_stmt = space_stmt.where(Shelf.owner_id.in_(owner_ids))
    
    space_query = space_stmt.group_by(SizeClass.name).subquery()

    # 2. Historical Growth (Last X days) - Unioned and filtered by owner and building
    lookback_dt = datetime.now(timezone.utc) - timedelta(days=params.lookback_days)
    divisor = max(params.lookback_days, 1) / 30.0
    
    item_growth = (
        select(Tray.id, Tray.size_class_id, Tray.owner_id, Tray.accession_dt)
        .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id)
        .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
        .join(Ladder, Shelf.ladder_id == Ladder.id)
        .join(Side, Ladder.side_id == Side.id)
        .join(Aisle, Side.aisle_id == Aisle.id)
        .join(Module, Aisle.module_id == Module.id)
        .join(Building, Module.building_id == Building.id)
        .where(Tray.accession_dt >= lookback_dt)
    )
    
    non_tray_growth = (
        select(NonTrayItem.id, NonTrayItem.size_class_id, NonTrayItem.owner_id, NonTrayItem.accession_dt)
        .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id)
        .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
        .join(Ladder, Shelf.ladder_id == Ladder.id)
        .join(Side, Ladder.side_id == Side.id)
        .join(Aisle, Side.aisle_id == Aisle.id)
        .join(Module, Aisle.module_id == Module.id)
        .join(Building, Module.building_id == Building.id)
        .where(NonTrayItem.accession_dt >= lookback_dt)
    )
    
    if owner_ids:
        item_growth = item_growth.where(Tray.owner_id.in_(owner_ids))
        non_tray_growth = non_tray_growth.where(NonTrayItem.owner_id.in_(owner_ids))
    
    if params.building_id:
        item_growth = item_growth.where(Building.id == params.building_id)
        non_tray_growth = non_tray_growth.where(Building.id == params.building_id)
    
    combined_items = union_all(item_growth, non_tray_growth).subquery()
    
    growth_query = (
        select(
            SizeClass.name.label("size_class_name"),
            (func.count(combined_items.c.id) / divisor).label("avg_monthly_growth")
        )
        .join(SizeClass, combined_items.c.size_class_id == SizeClass.id)
        .group_by(SizeClass.name)
    ).subquery()

    # 3. Join and calculate
    final_query = (
        select(
            space_query.c.size_class_name,
            space_query.c.current_available_space,
            func.coalesce(growth_query.c.avg_monthly_growth, 0).label("avg_monthly_accession_rate"),
            func.coalesce(
                space_query.c.current_available_space / func.nullif(growth_query.c.avg_monthly_growth, 0),
                99.9
            ).label("estimated_runway_months")
        )
        .join(growth_query, growth_query.c.size_class_name == space_query.c.size_class_name, isouter=True)
    )

    return session.execute(final_query).all()


@router.get("/capacity-forecast-height/", response_model=List[CapacityForecastHeightOutput])
def get_capacity_forecast_height(
    session: Session = Depends(get_session),
    params: CapacityForecastParams = Depends(),
):
    """
    Predictive: Storage runway in months for each physical shelf height.
    """
    owner_ids = None
    if params.owner_id:
        if params.include_sub_owners:
            owner_ids = get_owner_with_descendants(session, params.owner_id)
        else:
            owner_ids = [params.owner_id]

    # 1. Current Available Space (Grouped by physical height, filtered by owner/building)
    # Using cast to Float for more reliable grouping/joining on decimal values
    space_stmt = (
        select(
            sa.cast(Shelf.height, sa.Float).label("shelf_height"),
            func.sum(Shelf.available_space).label("current_available_space")
        )
    )
    
    if params.building_id:
        space_stmt = (
            space_stmt.join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)
            .join(Side, Ladder.side_id == Side.id, isouter=True)
            .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)
            .join(Module, Aisle.module_id == Module.id, isouter=True)
            .join(Building, Module.building_id == Building.id, isouter=True)
            .where(Building.id == params.building_id)
        )
    
    if owner_ids:
        space_stmt = space_stmt.where(Shelf.owner_id.in_(owner_ids))
    
    space_query = space_stmt.group_by(sa.cast(Shelf.height, sa.Float)).subquery()

    # 2. Historical Growth - Grouped by shelf height
    lookback_dt = datetime.now(timezone.utc) - timedelta(days=params.lookback_days)
    divisor = max(params.lookback_days, 1) / 30.0
    
    # Growth joins from items to shelves to get height
    item_growth_stmt = (
        select(Tray.id, sa.cast(Shelf.height, sa.Float).label("shelf_height"), Tray.owner_id)
        .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id)
        .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
        .where(Tray.accession_dt >= lookback_dt)
    )
    
    non_tray_growth_stmt = (
        select(NonTrayItem.id, sa.cast(Shelf.height, sa.Float).label("shelf_height"), NonTrayItem.owner_id)
        .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id)
        .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
        .where(NonTrayItem.accession_dt >= lookback_dt)
    )
    
    if owner_ids:
        item_growth_stmt = item_growth_stmt.where(Tray.owner_id.in_(owner_ids))
        non_tray_growth_stmt = non_tray_growth_stmt.where(NonTrayItem.owner_id.in_(owner_ids))
    
    if params.building_id:
        # Only join building chain if we actually need to filter by it
        item_growth_stmt = (
            item_growth_stmt.join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)
            .join(Side, Ladder.side_id == Side.id, isouter=True)
            .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)
            .join(Module, Aisle.module_id == Module.id, isouter=True)
            .join(Building, Module.building_id == Building.id, isouter=True)
            .where(Building.id == params.building_id)
        )
        non_tray_growth_stmt = (
            non_tray_growth_stmt.join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)
            .join(Side, Ladder.side_id == Side.id, isouter=True)
            .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)
            .join(Module, Aisle.module_id == Module.id, isouter=True)
            .join(Building, Module.building_id == Building.id, isouter=True)
            .where(Building.id == params.building_id)
        )
    
    combined_items = union_all(item_growth_stmt, non_tray_growth_stmt).subquery()
    
    growth_query = (
        select(
            combined_items.c.shelf_height,
            (func.count(combined_items.c.id) / divisor).label("avg_monthly_growth")
        )
        .group_by(combined_items.c.shelf_height)
    ).subquery()

    # 3. Join and calculate
    final_query = (
        select(
            space_query.c.shelf_height,
            space_query.c.current_available_space,
            func.coalesce(growth_query.c.avg_monthly_growth, 0).label("avg_monthly_accession_rate"),
            func.coalesce(
                space_query.c.current_available_space / func.nullif(growth_query.c.avg_monthly_growth, 0),
                99.9
            ).label("estimated_runway_months")
        )
        .join(growth_query, growth_query.c.shelf_height == space_query.c.shelf_height, isouter=True)
    )

    return session.execute(final_query).all()


@router.get("/daily-pulse/", response_model=DailyPulseOutput)
def get_daily_pulse(session: Session = Depends(get_session)):
    """
    Real-time Aggregate: Summary of today's facility throughput.
    """
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    accessioned = session.execute(select(func.count(Item.id)).where(Item.accession_dt >= today_start)).scalar() or 0
    shelved = session.execute(select(func.count(ShelvingJob.id)).where(ShelvingJob.last_transition >= today_start, ShelvingJob.status == "Completed")).scalar() or 0
    retrieved_tray = session.execute(select(func.count(ItemRetrievalEvent.id)).where(ItemRetrievalEvent.create_dt >= today_start)).scalar() or 0
    retrieved_non_tray = session.execute(select(func.count(NonTrayItemRetrievalEvent.id)).where(NonTrayItemRetrievalEvent.create_dt >= today_start)).scalar() or 0
    retrieved = retrieved_tray + retrieved_non_tray
    verified = session.execute(select(func.count(VerificationJob.id)).where(VerificationJob.last_transition >= today_start, VerificationJob.status == "Completed")).scalar() or 0
    pending = session.execute(select(func.count(Request.id)).where(Request.status == "New")).scalar() or 0
    verif_backlog = session.execute(select(func.count(VerificationJob.id)).where(VerificationJob.status != "Completed")).scalar() or 0

    return {
        "accessioned_today": accessioned,
        "shelved_today": shelved,
        "retrieved_today": retrieved,
        "verified_today": verified,
        "pending_requests": pending,
        "backlog_verification_jobs": verif_backlog
    }


@router.get("/exports/{dataset}/")
def export_raw_dataset(
    dataset: str,
    from_dt: Optional[datetime] = Query(None),
    to_dt: Optional[datetime] = Query(None),
    session: Session = Depends(get_session)
):
    """
    High-performance flat-file export for external BI tools (Tableau/PowerBI).
    """
def get_export_stmt_and_headers(dataset: str, from_dt: Optional[datetime], to_dt: Optional[datetime], session: Session):
    """
    Helper to get the SQL statement and headers for a given dataset.
    """
    if dataset == "items_master":
        # Flattened items with metadata
        TrayBarcode = aliased(Barcode)
        ShelfBarcode = aliased(Barcode)
        stmt = (
            select(
                Barcode.value.label("barcode"),
                TrayBarcode.value.label("tray_barcode"),
                Item.accession_dt,
                case(
                    (Item.tray_id.isnot(None), "Tray"),
                    else_="Non-Tray"
                ).label("item_type"),
                MediaType.name.label("media_type"),
                SizeClass.name.label("size_class"),
                Owner.name.label("owner"),
                Building.name.label("building"),
                Aisle.aisle_number,
                Module.module_number,
                Ladder.ladder_number,
                SideOrientation.name.label("side"),
                Shelf.shelf_number,
                ShelfPosition.position_number,
                ShelfBarcode.value.label("shelf_barcode"),
                Shelf.height.label("shelf_height_in"),
                Item.status
            )
            .join(Barcode, Item.barcode_id == Barcode.id, isouter=True)
            .join(SizeClass, Item.size_class_id == SizeClass.id, isouter=True)
            .join(Owner, Item.owner_id == Owner.id, isouter=True)
            .join(MediaType, Item.media_type_id == MediaType.id, isouter=True)
            .join(Tray, Item.tray_id == Tray.id, isouter=True)
            .join(TrayBarcode, Tray.barcode_id == TrayBarcode.id, isouter=True)
            .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id, isouter=True)
            .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)
            .join(ShelfBarcode, Shelf.barcode_id == ShelfBarcode.id, isouter=True)
            .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)
            .join(Side, Ladder.side_id == Side.id, isouter=True)
            .join(SideOrientation, Side.side_orientation_id == SideOrientation.id, isouter=True)
            .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)
            .join(Module, Aisle.module_id == Module.id, isouter=True)
            .join(Building, Module.building_id == Building.id, isouter=True)
            # .distinct() removed here to prevent timeout of the very large exports. FETCH-1655
        )
        if from_dt: stmt = stmt.where(Item.accession_dt >= from_dt)
        if to_dt: stmt = stmt.where(Item.accession_dt <= to_dt)
        
        headers = [
            "barcode", "tray_barcode", "accession_date", "type", "media_type", "size_class", "owner", 
            "building", "aisle", "module", "ladder", "side", "shelf", "shelf_position", "shelf_barcode",
            "shelf_height", "status"
        ]
    elif dataset == "inventory_activity":
        # Build individual queries for each event type to avoid join ambiguity
        queries = []

        # 1. Accession (Item)
        q1 = select(
            literal("Accession").label("event_type"),
            Item.accession_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(Item.accession_job_id, BigInteger).label("job_number")
        ).select_from(Item)\
         .join(Barcode, Item.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, Item.owner_id == Owner.id, isouter=True)\
         .join(Tray, Item.tray_id == Tray.id, isouter=True)\
         .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q1 = q1.where(Item.accession_dt >= from_dt)
        if to_dt: q1 = q1.where(Item.accession_dt <= to_dt)
        queries.append(q1)

        # 2. Accession (NonTray)
        q2 = select(
            literal("Accession (NT)").label("event_type"),
            NonTrayItem.accession_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(NonTrayItem.accession_job_id, BigInteger).label("job_number")
        ).select_from(NonTrayItem)\
         .join(Barcode, NonTrayItem.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, NonTrayItem.owner_id == Owner.id, isouter=True)\
         .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q2 = q2.where(NonTrayItem.accession_dt >= from_dt)
        if to_dt: q2 = q2.where(NonTrayItem.accession_dt <= to_dt)
        queries.append(q2)

        # 3. Verification
        q3 = select(
            literal("Verification").label("event_type"),
            VerificationJob.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(VerificationJob.id, BigInteger).label("job_number")
        ).select_from(VerificationJob)\
         .join(Item, Item.verification_job_id == VerificationJob.id)\
         .join(Barcode, Item.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, Item.owner_id == Owner.id, isouter=True)\
         .join(Tray, Item.tray_id == Tray.id, isouter=True)\
         .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q3 = q3.where(VerificationJob.create_dt >= from_dt)
        if to_dt: q3 = q3.where(VerificationJob.create_dt <= to_dt)
        queries.append(q3)

        # 4. Verification (NonTray)
        q4 = select(
            literal("Verification (NT)").label("event_type"),
            VerificationJob.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(VerificationJob.id, BigInteger).label("job_number")
        ).select_from(VerificationJob)\
         .join(NonTrayItem, NonTrayItem.verification_job_id == VerificationJob.id)\
         .join(Barcode, NonTrayItem.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, NonTrayItem.owner_id == Owner.id, isouter=True)\
         .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q4 = q4.where(VerificationJob.create_dt >= from_dt)
        if to_dt: q4 = q4.where(VerificationJob.create_dt <= to_dt)
        queries.append(q4)

        # 5. Shelving
        q5 = select(
            literal("Shelving").label("event_type"),
            ShelvingJob.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(ShelvingJob.id, BigInteger).label("job_number")
        ).select_from(ShelvingJob)\
         .join(Tray, Tray.shelving_job_id == ShelvingJob.id)\
         .join(Item, Item.tray_id == Tray.id)\
         .join(Barcode, Item.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, Item.owner_id == Owner.id, isouter=True)\
         .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q5 = q5.where(ShelvingJob.create_dt >= from_dt)
        if to_dt: q5 = q5.where(ShelvingJob.create_dt <= to_dt)
        queries.append(q5)

        # 6. Shelving (NonTray)
        q6 = select(
            literal("Shelving (NT)").label("event_type"),
            ShelvingJob.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(ShelvingJob.id, BigInteger).label("job_number")
        ).select_from(ShelvingJob)\
         .join(NonTrayItem, NonTrayItem.shelving_job_id == ShelvingJob.id)\
         .join(Barcode, NonTrayItem.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, NonTrayItem.owner_id == Owner.id, isouter=True)\
         .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q6 = q6.where(ShelvingJob.create_dt >= from_dt)
        if to_dt: q6 = q6.where(ShelvingJob.create_dt <= to_dt)
        queries.append(q6)

        # 7. Request
        q7 = select(
            literal("Request").label("event_type"),
            Request.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(Request.id, BigInteger).label("job_number")
        ).select_from(Request)\
         .join(Item, Request.item_id == Item.id)\
         .join(Barcode, Item.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, Item.owner_id == Owner.id, isouter=True)\
         .join(Tray, Item.tray_id == Tray.id, isouter=True)\
         .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q7 = q7.where(Request.create_dt >= from_dt)
        if to_dt: q7 = q7.where(Request.create_dt <= to_dt)
        queries.append(q7)

        # 8. Request (NonTray)
        q8 = select(
            literal("Request (NT)").label("event_type"),
            Request.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(Request.id, BigInteger).label("job_number")
        ).select_from(Request)\
         .join(NonTrayItem, Request.non_tray_item_id == NonTrayItem.id)\
         .join(Barcode, NonTrayItem.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, NonTrayItem.owner_id == Owner.id, isouter=True)\
         .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q8 = q8.where(Request.create_dt >= from_dt)
        if to_dt: q8 = q8.where(Request.create_dt <= to_dt)
        queries.append(q8)

        # 9. Picklist
        q9 = select(
            literal("Picklist").label("event_type"),
            PickList.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(PickList.id, BigInteger).label("job_number")
        ).select_from(PickList)\
         .join(Request, Request.pick_list_id == PickList.id)\
         .join(Item, Request.item_id == Item.id)\
         .join(Barcode, Item.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, Item.owner_id == Owner.id, isouter=True)\
         .join(Tray, Item.tray_id == Tray.id, isouter=True)\
         .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q9 = q9.where(PickList.create_dt >= from_dt)
        if to_dt: q9 = q9.where(PickList.create_dt <= to_dt)
        queries.append(q9)

        # 10. Picklist (NonTray)
        q10 = select(
            literal("Picklist (NT)").label("event_type"),
            PickList.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(PickList.id, BigInteger).label("job_number")
        ).select_from(PickList)\
         .join(Request, Request.pick_list_id == PickList.id)\
         .join(NonTrayItem, Request.non_tray_item_id == NonTrayItem.id)\
         .join(Barcode, NonTrayItem.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, NonTrayItem.owner_id == Owner.id, isouter=True)\
         .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q10 = q10.where(PickList.create_dt >= from_dt)
        if to_dt: q10 = q10.where(PickList.create_dt <= to_dt)
        queries.append(q10)

        # 11. Retrieval
        q11 = select(
            literal("Retrieval").label("event_type"),
            ItemRetrievalEvent.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(ItemRetrievalEvent.pick_list_id, BigInteger).label("job_number")
        ).select_from(ItemRetrievalEvent)\
         .join(Item, ItemRetrievalEvent.item_id == Item.id)\
         .join(Barcode, Item.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, Item.owner_id == Owner.id, isouter=True)\
         .join(Tray, Item.tray_id == Tray.id, isouter=True)\
         .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q11 = q11.where(ItemRetrievalEvent.create_dt >= from_dt)
        if to_dt: q11 = q11.where(ItemRetrievalEvent.create_dt <= to_dt)
        queries.append(q11)

        # 12. Retrieval (NonTray)
        q12 = select(
            literal("Retrieval (NT)").label("event_type"),
            NonTrayItemRetrievalEvent.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(NonTrayItemRetrievalEvent.pick_list_id, BigInteger).label("job_number")
        ).select_from(NonTrayItemRetrievalEvent)\
         .join(NonTrayItem, NonTrayItemRetrievalEvent.non_tray_item_id == NonTrayItem.id)\
         .join(Barcode, NonTrayItem.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, NonTrayItem.owner_id == Owner.id, isouter=True)\
         .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q12 = q12.where(NonTrayItemRetrievalEvent.create_dt >= from_dt)
        if to_dt: q12 = q12.where(NonTrayItemRetrievalEvent.create_dt <= to_dt)
        queries.append(q12)

        # 13. Refile
        q13 = select(
            literal("Refile").label("event_type"),
            RefileJob.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(RefileJob.id, BigInteger).label("job_number")
        ).select_from(RefileJob)\
         .join(RefileItem, RefileItem.refile_job_id == RefileJob.id)\
         .join(Item, RefileItem.item_id == Item.id)\
         .join(Barcode, Item.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, Item.owner_id == Owner.id, isouter=True)\
         .join(Tray, Item.tray_id == Tray.id, isouter=True)\
         .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q13 = q13.where(RefileJob.create_dt >= from_dt)
        if to_dt: q13 = q13.where(RefileJob.create_dt <= to_dt)
        queries.append(q13)

        # 14. Refile (NonTray)
        q14 = select(
            literal("Refile (NT)").label("event_type"),
            RefileJob.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(RefileJob.id, BigInteger).label("job_number")
        ).select_from(RefileJob)\
         .join(RefileNonTrayItem, RefileNonTrayItem.refile_job_id == RefileJob.id)\
         .join(NonTrayItem, RefileNonTrayItem.non_tray_item_id == NonTrayItem.id)\
         .join(Barcode, NonTrayItem.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, NonTrayItem.owner_id == Owner.id, isouter=True)\
         .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q14 = q14.where(RefileJob.create_dt >= from_dt)
        if to_dt: q14 = q14.where(RefileJob.create_dt <= to_dt)
        queries.append(q14)

        # 15. Withdrawal
        q15 = select(
            literal("Withdrawal").label("event_type"),
            WithdrawJob.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(WithdrawJob.id, BigInteger).label("job_number")
        ).select_from(WithdrawJob)\
         .join(ItemWithdrawal, ItemWithdrawal.withdraw_job_id == WithdrawJob.id)\
         .join(Item, ItemWithdrawal.item_id == Item.id)\
         .join(Barcode, Item.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, Item.owner_id == Owner.id, isouter=True)\
         .join(Tray, Item.tray_id == Tray.id, isouter=True)\
         .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q15 = q15.where(WithdrawJob.create_dt >= from_dt)
        if to_dt: q15 = q15.where(WithdrawJob.create_dt <= to_dt)
        queries.append(q15)

        # 16. Withdrawal (NonTray)
        q16 = select(
            literal("Withdrawal (NT)").label("event_type"),
            WithdrawJob.create_dt.label("event_dt"),
            Barcode.value.label("item_barcode"),
            Owner.name.label("owner"),
            Building.name.label("building"),
            cast(WithdrawJob.id, BigInteger).label("job_number")
        ).select_from(WithdrawJob)\
         .join(NonTrayItemWithdrawal, NonTrayItemWithdrawal.withdraw_job_id == WithdrawJob.id)\
         .join(NonTrayItem, NonTrayItemWithdrawal.non_tray_item_id == NonTrayItem.id)\
         .join(Barcode, NonTrayItem.barcode_id == Barcode.id, isouter=True)\
         .join(Owner, NonTrayItem.owner_id == Owner.id, isouter=True)\
         .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id, isouter=True)\
         .join(Shelf, ShelfPosition.shelf_id == Shelf.id, isouter=True)\
         .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)\
         .join(Side, Ladder.side_id == Side.id, isouter=True)\
         .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)\
         .join(Module, Aisle.module_id == Module.id, isouter=True)\
         .join(Building, Module.building_id == Building.id, isouter=True)
        if from_dt: q16 = q16.where(WithdrawJob.create_dt >= from_dt)
        if to_dt: q16 = q16.where(WithdrawJob.create_dt <= to_dt)
        queries.append(q16)

        # Build union and select from it for ordering
        union_stmt = union_all(*queries).alias("activity_union")
        stmt = select(
            union_stmt.c.event_type,
            union_stmt.c.event_dt,
            union_stmt.c.item_barcode,
            union_stmt.c.owner,
            union_stmt.c.building,
            union_stmt.c.job_number
        ).select_from(union_stmt).order_by(union_stmt.c.event_dt.desc())

        headers = ["event_type", "event_dt", "item_barcode", "owner", "building", "job_number"]


    elif dataset == "facility_footprint":
        # Comprehensive shelf utilization and path
        from app.models.shelf_types import ShelfType
        ShelfBarcode = aliased(Barcode)
        stmt = (
            select(
                Building.name.label("building"),
                Module.module_number.label("module"),
                Aisle.aisle_number.label("aisle"),
                SideOrientation.name.label("side"),
                Ladder.ladder_number.label("ladder"),
                Shelf.shelf_number.label("shelf"),
                ShelfBarcode.value.label("shelf_barcode"),
                Shelf.height.label("height"),
                Shelf.width.label("width"),
                Shelf.depth.label("depth"),
                ShelfType.type.label("shelf_type"),
                SizeClass.name.label("size_class"),
                Owner.name.label("assigned_owner"),
                ShelfType.max_capacity.label("total_slots"),
                Shelf.available_space.label("available_slots"),
                (ShelfType.max_capacity - Shelf.available_space).label("used_slots")
            )
            .join(Ladder, Shelf.ladder_id == Ladder.id, isouter=True)
            .join(Side, Ladder.side_id == Side.id, isouter=True)
            .join(SideOrientation, Side.side_orientation_id == SideOrientation.id, isouter=True)
            .join(Aisle, Side.aisle_id == Aisle.id, isouter=True)
            .join(Module, Aisle.module_id == Module.id, isouter=True)
            .join(Building, Module.building_id == Building.id, isouter=True)
            .join(ShelfType, Shelf.shelf_type_id == ShelfType.id, isouter=True)
            .join(ShelfBarcode, Shelf.barcode_id == ShelfBarcode.id, isouter=True)
            .join(Owner, Shelf.owner_id == Owner.id, isouter=True)
            .join(SizeClass, ShelfType.size_class_id == SizeClass.id, isouter=True)
            .order_by(Building.name, Module.module_number, Aisle.aisle_number, Shelf.shelf_number)
        )
        headers = [
            "building", "module", "aisle", "side", "ladder", "shelf", "shelf_barcode",
            "height", "width", "depth", "shelf_type", "size_class", 
            "assigned_owner", "total_slots", "available_slots", "used_slots"
        ]
    
    else:
        raise HTTPException(status_code=400, detail="Invalid dataset requested")

    return stmt, headers


# NOTE: The on-demand /exports/ endpoint has been removed. 
# All raw data exports must now be created via the /scheduled-exports/ system
# to ensure background processing and compression.

@router.post("/scheduled-exports/", response_model=ScheduledExportRead)
def create_scheduled_export(
    payload: ScheduledExportCreate,
    session: Session = Depends(get_session)
):
    """
    Schedules a new raw data export.
    """
    new_export = ScheduledExport(
        name=payload.name,
        dataset=payload.dataset,
        filters=payload.filters,
        schedule_type=payload.schedule_type,
        frequency=payload.frequency,
        retention_days=payload.retention_days,
        next_run_at=payload.start_at
    )
    session.add(new_export)
    session.commit()
    session.refresh(new_export)
    return new_export

@router.get("/scheduled-exports/", response_model=List[ScheduledExportRead])
def list_scheduled_exports(session: Session = Depends(get_session)):
    """
    Lists all active and inactive export schedules.
    """
    return session.execute(select(ScheduledExport)).scalars().all()

@router.delete("/scheduled-exports/{export_id}")
def delete_scheduled_export(export_id: int, session: Session = Depends(get_session)):
    """
    Deletes a scheduled export configuration.
    """
    export = session.get(ScheduledExport, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Schedule not found")
    session.delete(export)
    session.commit()
    return {"message": "Schedule deleted"}

@router.get("/export-history/", response_model=List[ExportHistoryRead])
def list_export_history(session: Session = Depends(get_session)):
    """
    Lists all generated export files that haven't expired yet.
    """
    return session.execute(
        select(ExportHistory)
        .where(ExportHistory.expires_at > datetime.now(timezone.utc))
        .order_by(ExportHistory.id.desc())
    ).scalars().all()

@router.get("/export-history/download/{history_id}")
def download_historical_export(history_id: int, session: Session = Depends(get_session)):
    """
    Downloads a previously generated export file from server storage.
    """
    history = session.get(ExportHistory, history_id)
    if not history:
        raise HTTPException(status_code=404, detail="Export record not found")
    
    if not os.path.exists(history.file_path):
        raise HTTPException(status_code=404, detail="Physical file missing from server storage")
    
    return FileResponse(
        history.file_path,
        media_type="application/x-gzip",
        filename=history.filename
    )
