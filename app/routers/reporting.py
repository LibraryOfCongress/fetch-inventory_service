import csv
from io import StringIO
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy import func, union_all, literal, and_, or_
from sqlmodel import Session, select

from app.database.session import get_session
from app.logger import inventory_logger
from app.filter_params import ShelvingJobDiscrepancyParams, OpenLocationParams
from app.models.items import Item
from app.models.media_types import MediaType
from app.models.non_tray_items import NonTrayItem
from app.models.owners import Owner
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
from app.schemas.reporting import AccessionItemsDetailOutput, ShelvingJobDiscrepancyOutput, OpenLocationsOutput
from app.config.exceptions import (
    NotFound
)


router = APIRouter(
    prefix="/reporting",
    tags=["reporting"],
)


@router.get("/accession-items", response_model=Page[AccessionItemsDetailOutput])
def get_accessioned_items_aggregate(
    session: Session = Depends(get_session),
    owner_id: list[int] = Query(default=None),
    size_class_id: list[int] = Query(default=None),
    media_type_id: list[int] = Query(default=None),
    from_dt: datetime = Query(default=None),
    to_dt: datetime = Query(default=None),
):
    item_query_conditions = []
    non_tray_item_query_conditions = []
    selection = []
    group_by = []

    try:
        if owner_id:
            item_query_conditions.append(Item.owner_id.in_(owner_id))
            non_tray_item_query_conditions.append(NonTrayItem.owner_id.in_(owner_id))
        if size_class_id:
            item_query_conditions.append(Item.size_class_id.in_(size_class_id))
            non_tray_item_query_conditions.append(
                NonTrayItem.size_class_id.in_(size_class_id)
            )
        if media_type_id:
            item_query_conditions.append(Item.media_type_id.in_(media_type_id))
            non_tray_item_query_conditions.append(
                NonTrayItem.media_type_id.in_(media_type_id)
            )
        if from_dt:
            item_query_conditions.append(Item.accession_dt >= from_dt)
            non_tray_item_query_conditions.append(NonTrayItem.accession_dt >= from_dt)
        if to_dt:
            item_query_conditions.append(Item.accession_dt <= to_dt)
            non_tray_item_query_conditions.append(NonTrayItem.accession_dt <= to_dt)

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

        if owner_id:
            selection.append(combined_query.c.owner_name)
            group_by.append(combined_query.c.owner_name)
        if size_class_id:
            selection.append(combined_query.c.size_class_name)
            group_by.append(combined_query.c.size_class_name)
        if media_type_id:
            selection.append(combined_query.c.media_type_name)
            group_by.append(combined_query.c.media_type_name)

        if not selection:
            final_query = select(
                literal("All").label("owner_name"),
                literal("All").label("size_class_name"),
                literal("All").label("media_type_name"),
                func.count().label("count"),
            ).select_from(combined_query)

        else:
            final_query = select(
                *selection,
                func.count().label("count"),
            ).group_by(*group_by)

        return paginate(session, final_query)

    except Exception as e:
        inventory_logger.error(e)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


# SHELVING JOB DISCREPANCIES
@router.get("/shelving-job-discrepancies/", response_model=Page[ShelvingJobDiscrepancyOutput])
def get_shelving_job_discrepancy_list(
    session: Session = Depends(get_session),
    params: ShelvingJobDiscrepancyParams = Depends()
) -> list:
    """
    Returns a list of ShelvingJobDiscrepancy objects.
    """
    query = select(ShelvingJobDiscrepancy).distinct()
    if params.shelving_job_id:
        query = query.where(ShelvingJobDiscrepancy.shelving_job_id == params.shelving_job_id)
    if params.assigned_user_id:
        query = query.where(ShelvingJobDiscrepancy.assigned_user_id == params.assigned_user_id)
    if params.owner_id:
        query = query.where(ShelvingJobDiscrepancy.owner_id == params.owner_id)
    if params.size_class_id:
        query = query.where(ShelvingJobDiscrepancy.size_class_id == params.size_class_id)
    if params.from_dt:
        query = query.where(ShelvingJobDiscrepancy.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(ShelvingJobDiscrepancy.create_dt <= params.to_dt)

    return paginate(session, query)


@router.get("/shelving-job-discrepancies/download", response_class=StreamingResponse)
def get_shelving_job_report_csv(
    session: Session = Depends(get_session),
    params: ShelvingJobDiscrepancyParams = Depends()
):
    """
    Translates list response of ShelvingJobDiscrepancy objects to csv,
    returns binary for download
    """
    query = select(ShelvingJobDiscrepancy).distinct()

    if params.shelving_job_id:
        query = query.where(ShelvingJobDiscrepancy.shelving_job_id == params.shelving_job_id)
    if params.assigned_user_id:
        query = query.where(ShelvingJobDiscrepancy.assigned_user_id == params.assigned_user_id)
    if params.owner_id:
        query = query.where(ShelvingJobDiscrepancy.owner_id == params.owner_id)
    if params.size_class_id:
        query = query.where(ShelvingJobDiscrepancy.size_class_id == params.size_class_id)
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
    writer.writerow([
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
        "update_dt"
    ])

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
        writer.writerow([
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
            row.update_dt
        ])

    # Reset the buffer position
    output.seek(0)

    # Create a StreamingResponse
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shelving_discrepancies.csv"}
    )

@router.get("/shelving-job-discrepancies/{id}", response_model=ShelvingJobDiscrepancyOutput)
def get_shelving_job_discrepancy_detail(id: int, session: Session = Depends(get_session)):
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
    params: OpenLocationParams = Depends()
) -> list:
    """
    Returns a paginated list of shelf objects with
    unoccupied nested shelf positions based on search criteria
    """
    total_positions_subquery = (
        select(
            ShelfPosition.shelf_id,
            func.count(ShelfPosition.id).label("total_positions")
        )
        .group_by(ShelfPosition.shelf_id)
        .subquery()
    )

    occupied_positions_subquery = (
        select(
            ShelfPosition.shelf_id,
            func.count(ShelfPosition.id).label("occupied_positions")
        )
        .where(
            or_(
                ShelfPosition.tray != None,
                ShelfPosition.non_tray_item != None
            )
        )
        .group_by(ShelfPosition.shelf_id)
        .subquery()
    )

    shelf_query = (
        select(
            Shelf
        ).distinct().join(
            ShelfType, Shelf.shelf_type_id == ShelfType.id
        ).join(
            SizeClass, ShelfType.size_class_id == SizeClass.id
        ).join(
            Shelf.barcode
        ).join(
            Shelf.owner
        ).outerjoin(
            total_positions_subquery, Shelf.id == total_positions_subquery.c.shelf_id
        ).outerjoin(
            occupied_positions_subquery, Shelf.id == occupied_positions_subquery.c.shelf_id
        )
    )

    if params.show_partial == False:
        # Show shelves with no occupied positions
        shelf_query = shelf_query.where(
            func.coalesce(occupied_positions_subquery.c.occupied_positions, 0) == 0
        )
    else:
        # Show shelves with at least some space available
        shelf_query = shelf_query.where(
            func.coalesce(occupied_positions_subquery.c.occupied_positions, 0) < ShelfType.max_capacity
        )

    if params.owner_id:
        shelf_query = shelf_query.where(Shelf.owner_id == params.owner_id)
    if params.size_class_id:
        shelf_query = shelf_query.where(ShelfType.size_class_id == params.size_class_id)
    if params.height:
        shelf_query = shelf_query.where(Shelf.height == params.height)
    if params.width:
        shelf_query = shelf_query.where(Shelf.width == params.width)
    if params.depth:
        shelf_query = shelf_query.where(Shelf.depth == params.depth)

    # Now location constraints
    if params.ladder_id:
        # shelf_query = shelf_query.where(Shelf.ladder_id == params.ladder_id)
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).where(
            Ladder.id == params.ladder_id
        )
    elif params.side_id:
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).where(
            Side.id == params.side_id
        )
    elif params.aisle_id:
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).join(
            Aisle, Side.aisle_id == Aisle.id
        ).where(
            Aisle.id == params.aisle_id
        )
    elif params.module_id:
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).join(
            Aisle, Side.aisle_id == Aisle.id
        ).join(
            Module, Aisle.module_id == Module.id
        ).where(
            Module.id == params.module_id
        )
    elif params.building_id:
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).join(
            Aisle, Side.aisle_id == Aisle.id
        ).join(
            Module, Aisle.module_id == Module.id
        ).join(
            Building, Module.building_id == Building.id
        ).where(
            Building.id == params.building_id
        )

    return paginate(session, shelf_query)


@router.get("/open-locations/download", response_class=StreamingResponse)
def get_open_locations_csv(
    session: Session = Depends(get_session),
    params: OpenLocationParams = Depends()
) -> list:
    """
    Returns a csv report of shelf objects with
    unoccupied nested shelf positions based on search criteria
    """
    total_positions_subquery = (
        select(
            ShelfPosition.shelf_id,
            func.count(ShelfPosition.id).label("total_positions")
        )
        .group_by(ShelfPosition.shelf_id)
        .subquery()
    )

    occupied_positions_subquery = (
        select(
            ShelfPosition.shelf_id,
            func.count(ShelfPosition.id).label("occupied_positions")
        )
        .where(
            or_(
                ShelfPosition.tray != None,
                ShelfPosition.non_tray_item != None
            )
        )
        .group_by(ShelfPosition.shelf_id)
        .subquery()
    )

    shelf_query = (
        select(
            Shelf
        ).distinct().join(
            ShelfType, Shelf.shelf_type_id == ShelfType.id
        ).join(
            SizeClass, ShelfType.size_class_id == SizeClass.id
        ).join(
            Shelf.barcode
        ).join(
            Shelf.owner
        ).outerjoin(
            total_positions_subquery, Shelf.id == total_positions_subquery.c.shelf_id
        ).outerjoin(
            occupied_positions_subquery, Shelf.id == occupied_positions_subquery.c.shelf_id
        )
    )

    if params.show_partial == False:
        # Show shelves with no occupied positions
        shelf_query = shelf_query.where(
            func.coalesce(occupied_positions_subquery.c.occupied_positions, 0) == 0
        )
    else:
        # Show shelves with at least some space available
        shelf_query = shelf_query.where(
            func.coalesce(occupied_positions_subquery.c.occupied_positions, 0) < ShelfType.max_capacity
        )

    if params.owner_id:
        shelf_query = shelf_query.where(Shelf.owner_id == params.owner_id)
    if params.size_class_id:
        shelf_query = shelf_query.where(ShelfType.size_class_id == params.size_class_id)
    if params.height:
        shelf_query = shelf_query.where(Shelf.height == params.height)
    if params.width:
        shelf_query = shelf_query.where(Shelf.width == params.width)
    if params.depth:
        shelf_query = shelf_query.where(Shelf.depth == params.depth)

    # Now location constraints
    if params.ladder_id:
        # shelf_query = shelf_query.where(Shelf.ladder_id == params.ladder_id)
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).where(
            Ladder.id == params.ladder_id
        )
    elif params.side_id:
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).where(
            Side.id == params.side_id
        )
    elif params.aisle_id:
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).join(
            Aisle, Side.aisle_id == Aisle.id
        ).where(
            Aisle.id == params.aisle_id
        )
    elif params.module_id:
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).join(
            Aisle, Side.aisle_id == Aisle.id
        ).join(
            Module, Aisle.module_id == Module.id
        ).where(
            Module.id == params.module_id
        )
    elif params.building_id:
        shelf_query = shelf_query.join(
            Ladder, Shelf.ladder_id == Ladder.id
        ).join(
            Side, Ladder.side_id == Side.id
        ).join(
            Aisle, Side.aisle_id == Aisle.id
        ).join(
            Module, Aisle.module_id == Module.id
        ).join(
            Building, Module.building_id == Building.id
        ).where(
            Building.id == params.building_id
        )

    result = session.execute(shelf_query)
    rows = result.scalars().all()

        # Create an in-memory CSV
    output = StringIO()
    writer = csv.writer(output)

    # Write headers (optional: use column names dynamically)
    writer.writerow([
        "shelf_barcode",
        "available_space",
        "location",
        "owner",
        "height",
        "width",
        "depth",
        "size_class"
    ])

    # Write rows
    for row in rows:
        writer.writerow([
            row.barcode.value,
            row.available_space,
            row.location,
            row.owner.name,
            row.height,
            row.width,
            row.depth,
            row.shelf_type.size_class.short_name
        ])

    # Reset the buffer position
    output.seek(0)

    # Create a StreamingResponse
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=open_locations.csv"}
    )
