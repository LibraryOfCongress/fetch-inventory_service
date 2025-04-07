import math
from datetime import timedelta, datetime
from enum import Enum
from typing import List, Dict, Tuple, Any
from typing_extensions import Annotated
import logging

import pandas as pd
import pytz
from datetime import timezone
from sqlalchemy import and_, text, asc, desc, func, column, or_
from sqlalchemy.orm import joinedload, aliased, RelationshipProperty
from sqlalchemy.inspection import inspect
from sqlalchemy.sql import not_
from sqlmodel import select, Session
from fastapi import Header, Depends

from app.database.session import get_session, session_manager
from app.config.exceptions import NotFound, BadRequest
from app.logger import inventory_logger
from app.models.aisle_numbers import AisleNumber
from app.models.barcodes import Barcode
from app.models.buildings import Building
from app.models.container_types import ContainerType
from app.models.delivery_locations import DeliveryLocation
from app.models.item_withdrawals import ItemWithdrawal
from app.models.items import Item
from app.models.ladder_numbers import LadderNumber
from app.models.media_types import MediaType
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.non_tray_items import NonTrayItem
from app.models.owners import Owner
from app.models.priorities import Priority
from app.models.request_types import RequestType
from app.models.requests import Request
from app.models.shelf_numbers import ShelfNumber
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.side_orientations import SideOrientation
from app.models.sides import Side
from app.models.ladders import Ladder
from app.models.shelves import Shelf
from app.models.shelf_types import ShelfType
from app.models.shelf_positions import ShelfPosition
from app.models.size_class import SizeClass
from app.models.tray_withdrawal import TrayWithdrawal
from app.models.trays import Tray
from app.models.users import User
from app.models.withdraw_jobs import WithdrawJob

LOGGER = logging.getLogger(__name__)


def get_module_shelf_position(session, shelf_position):
    """
    Retrieves the module associated with a given shelf position.
    **Args:**
    -  Shelf Position: The shelf position object containing the shelf ID.

    **Returns:**
    - Module: The module associated with the shelf position.

    **Raises:**
    - NotFound: If any of the related objects (shelf, ladder, side, aisle, module)
    are not found.
    """
    shelf = (
        session.query(Shelf)
        .options(joinedload(Shelf.ladder))
        .filter(Shelf.id == shelf_position.shelf_id)
        .first()
    )

    if not shelf:
        raise NotFound(detail=f"Shelf ID {shelf_position.shelf_id} Not Found")

    ladder = shelf.ladder

    if not ladder:
        raise NotFound(detail=f"Ladder ID {shelf.ladder_id} Not Found")

    side = ladder.side

    if not side:
        raise NotFound(detail=f"Side ID {ladder.side_id} Not Found")

    aisle = side.aisle

    if not aisle:
        raise NotFound(detail=f"Aisle ID {side.aisle_id} Not Found")

    module = aisle.module

    if not module:
        raise NotFound(detail=f"Module ID {aisle.module_id} Not Found")

    return module


def get_location(session, shelf_position):
    """
    Retrieves the related location data for a given shelf position.

    **Args:**
    - shelf_position (ShelfPosition): The shelf position object containing the
    shelf ID.

    **Returns:**
    dict: A dictionary containing the related location data. The dictionary has the
    following keys:
    - "aisle" (Aisle): The aisle object associated with the shelf position.
    - "ladder" (Ladder): The ladder object associated with the shelf position.
    - "shelf" (Shelf): The shelf object associated with the shelf position.

    **Raises:**
    - NotFound: If any of the related objects (shelf, ladder, aisle) are not found.
    """
    shelf_query = select(Shelf).filter(Shelf.id == shelf_position.shelf_id)

    ladder_query = (
        select(Ladder)
        .join(Shelf)
        .where(Ladder.id == shelf_query.subquery().c.ladder_id)
    )

    aisle_query = (
        select(Aisle)
        .join(Side)
        .join(Ladder)
        .where(Side.id == ladder_query.subquery().c.side_id)
        .where(Aisle.id == Side.aisle_id)
    )

    shelf = session.exec(shelf_query).first()
    ladder = session.exec(ladder_query).first()
    aisle = session.exec(aisle_query).first()

    if not shelf:
        raise NotFound(detail=f"Shelf ID {shelf_position.shelf_id} Not Found")

    if not ladder:
        raise NotFound(detail=f"Ladder ID {shelf.ladder_id} Not Found")

    if not aisle:
        raise NotFound(detail=f"Aisle ID {ladder.aisle_id} Not Found")

    shelf_number_query = select(ShelfNumber).where(
        ShelfNumber.id == shelf.shelf_number_id
    )

    ladder_number_query = select(LadderNumber).where(
        LadderNumber.id == ladder.ladder_number_id
    )

    aisle_number_query = select(AisleNumber).where(
        AisleNumber.id == aisle.aisle_number_id
    )

    shelf_number = session.exec(shelf_number_query).first()
    ladder_number = session.exec(ladder_number_query).first()
    aisle_number = session.exec(aisle_number_query).first()

    return {
        "aisle": aisle,
        "ladder": ladder,
        "shelf": shelf,
        "shelf_number": shelf_number,
        "ladder_number": ladder_number,
        "aisle_number": aisle_number,
    }


def process_containers_for_shelving(
    session,
    container_type,
    containers,
    shelving_job_id,
    building_id,
    module_id,
    aisle_id,
    side_id,
    ladder_id,
):
    """
    Given a container and location params,
    assigns an available shelf position id
    to both a container's proposed and actual shelf position.
    Shelving Job completion later updates the actual shelf position
    if needed.

    Size classes among containers within the job can vary.

    params:
        - session is db session yielded in path operation
        - container_type tracks 'Tray' or 'Non-Tray'
        - Containers can either be tray or non-tray-item list
        - location id's are integers

    returns:
        - Nothing
        - Commits transactions
    """

    # conditions are where clauses
    conditions = []

    # perform joins from most constrained to least, for efficiency
    if ladder_id:
        conditions.append(Shelf.ladder_id == ladder_id)
    elif side_id:
        conditions.append(Ladder.side_id == side_id)
    elif aisle_id:
        conditions.append(Side.aisle_id == aisle_id)
    elif module_id:
        conditions.append(Aisle.module_id == module_id)
    else:
        # searching in aisles belonging to a building's modules
        conditions.append(Module.building_id == building_id)

    # query is built without execution beforehand
    # query is built without execution beforehand
    shelf_position_query = (
        select(
            ShelfPosition.id.label("shelf_position_id"),
            ShelfPosition.shelf_id,
            ShelfPosition.location,
            ShelfPositionNumber.number,
            Shelf.owner_id,
            Shelf.ladder_id,
            Ladder.side_id,
            Side.aisle_id,
            Aisle.module_id,
            Module.building_id,
            ShelfType.size_class_id,
        )
        .join(
            ShelfPositionNumber,
            ShelfPositionNumber.id == ShelfPosition.shelf_position_number_id,
        )
        .join(Shelf, Shelf.id == ShelfPosition.shelf_id)
        .join(ShelfType, ShelfType.id == Shelf.shelf_type_id)
        .join(Ladder, Ladder.id == Shelf.ladder_id)
        .join(Side, Side.id == Ladder.side_id)
        .join(Aisle, Aisle.id == Side.aisle_id)
        .join(Module, Module.id == Aisle.module_id)
        .where(
            not_(
                select(Tray)
                .where(
                    or_(
                        Tray.shelf_position_id == ShelfPosition.id,
                        Tray.shelf_position_proposed_id == ShelfPosition.id,
                    )
                )
                .exists()
            )
        )
        .where(
            not_(
                select(NonTrayItem)
                .where(
                    or_(
                        NonTrayItem.shelf_position_id == ShelfPosition.id,
                        NonTrayItem.shelf_position_proposed_id == ShelfPosition.id,
                    )
                )
                .exists()
            )
        )
    )

    # Group containers by (size_class_id, owner_id)
    containers_by_group = {}
    for container in containers:
        key = (container.size_class_id, container.owner_id)
        containers_by_group.setdefault(key, []).append(container)

    # Process each group individually.
    for (size_class_id, owner_id), container_group in containers_by_group.items():
        num_to_assign = len(container_group)

        # Build a query for available shelves  matching the container's size class and
        # owner.
        # and then by group the shelves ASC order.
        available_shelf_query = (
            shelf_position_query.where(
                and_(
                    ShelfType.size_class_id == size_class_id,
                    Shelf.owner_id == owner_id,
                    *conditions,
                )
            )
            .order_by(asc(ShelfPosition.location))
            .limit(num_to_assign)
        )

        # Execute the query.
        fetched_available_shelf_query = session.exec(available_shelf_query).all()

        if len(fetched_available_shelf_query) < num_to_assign:
            raise NotFound(
                detail="Not enough empty shelf positions for containers with "
                "size class and owner."
            )

        shelf_ids = list({item.shelf_id for item in fetched_available_shelf_query})

        # Build a query for available shelf positions matching the container's size class and owner.
        available_positions_query = (
            select(ShelfPosition)
            .where(ShelfPosition.shelf_id.in_(shelf_ids))
            .where(
                not_(
                    select(Tray)
                    .where(
                        or_(
                            Tray.shelf_position_id == ShelfPosition.id,
                            Tray.shelf_position_proposed_id == ShelfPosition.id,
                        )
                    )
                    .exists()
                )
            )
            .where(
                not_(
                    select(NonTrayItem)
                    .where(
                        or_(
                            NonTrayItem.shelf_position_id == ShelfPosition.id,
                            NonTrayItem.shelf_position_proposed_id == ShelfPosition.id,
                        )
                    )
                    .exists()
                )
            )
        )

        # Execute the query.
        shelf_positions = session.exec(available_positions_query).all()

        if len(shelf_positions) < num_to_assign:
            raise NotFound(
                detail="Not enough empty shelf positions for containers with size "
                "class and owner."
            )

        available_positions = sorted(
            shelf_positions,
            key=lambda pos: (
                pos.location.split("-")[:6],
                -int(pos.location.split("-")[-1]),
            ),
        )

        # Zip the container group with the available positions.
        for container, position in zip(container_group, available_positions):
            container.shelf_position_proposed_id = position.id
            container.shelving_job_id = shelving_job_id
            session.add(container)

        session.commit()

    return


def make_aware(dt):
    """
    Make a datetime object timezone-aware.
    """
    if dt.tzinfo is None:
        return pytz.utc.localize(dt)
    return dt


def manage_transition(original_record, update_record):
    """
    Task manages transition logic for running state.
    - updates run_time
    - tracks last_transition
    """
    run_timestamp = make_aware(update_record.run_timestamp)

    if original_record.run_time is None:
        original_record.run_time = timedelta(0)

    should_update_run_time = False

    # Define transitions where run_time should be updated
    transition_pairs = {
        ("Running", "Paused"),
        ("Running", "Completed"),
        ("Running", "Canceled"),
    }

    if (original_record.status, update_record.status) in transition_pairs:
        should_update_run_time = True

    if should_update_run_time:
        if original_record.last_transition:
            last_transition = make_aware(original_record.last_transition)
            original_record.run_time += run_timestamp - last_transition
        elif not original_record.last_transition:
            create_dt = make_aware(original_record.create_dt)
            original_record.run_time += run_timestamp - create_dt

        original_record.last_transition = run_timestamp

    return original_record


def get_refile_queue(params):
    """
    Get refile queue
    """
    # Base query for items
    item_query_conditions = []
    non_tray_item_query_conditions = []

    if params.building_id:
        item_query_conditions.append(Building.id == params.building_id)
        non_tray_item_query_conditions.append(Building.id == params.building_id)
    if params.media_type:
        media_type_subquery = select(MediaType.id).where(
            MediaType.name.in_(params.media_type)
        )
        item_query_conditions.append(Item.media_type_id.in_(media_type_subquery))
        non_tray_item_query_conditions.append(
            NonTrayItem.media_type_id.in_(media_type_subquery)
        )
    if params.owner:
        owner_subquery = select(Owner.id).where(Owner.name.in_(params.owner))
        item_query_conditions.append(Item.owner_id.in_(owner_subquery))
        non_tray_item_query_conditions.append(NonTrayItem.owner_id.in_(owner_subquery))
    if params.size_class:
        size_class_subquery = select(SizeClass.id).where(
            SizeClass.name.in_(params.size_class)
        )
        item_query_conditions.append(Item.size_class_id.in_(size_class_subquery))
        non_tray_item_query_conditions.append(
            NonTrayItem.size_class_id.in_(size_class_subquery)
        )

    if params.container_type:
        container_type_subquery = select(ContainerType.id).where(
            ContainerType.type.in_(params.container_type)
        )
        inventory_logger.info(f"Container Type Subquery: {container_type_subquery}")
        item_query_conditions.append(
            Tray.container_type_id.in_(container_type_subquery)
        )
        non_tray_item_query_conditions.append(
            NonTrayItem.container_type_id.in_(container_type_subquery)
        )

    # Get items scanned for refile queue
    item_query_conditions.append(Item.scanned_for_refile_queue == True)
    non_tray_item_query_conditions.append(NonTrayItem.scanned_for_refile_queue == True)

    item_query = (
        select(
            Item.id.label("id"),
            Barcode.value.label("barcode_value"),
            ShelfPosition.id.label("shelf_position_id"),
            ShelfPosition.location.label("location"),
            ShelfPosition.internal_location.label("internal_location"),
            ShelfPositionNumber.number.label("shelf_position_number"),
            ShelfPosition.shelf_id.label("shelf_id"),
            ShelfNumber.number.label("shelf_number"),
            Ladder.id.label("ladder_id"),
            LadderNumber.number.label("ladder_number"),
            Side.id.label("side_id"),
            SideOrientation.name.label("side_orientation"),
            Aisle.id.label("aisle_id"),
            AisleNumber.number.label("aisle_number"),
            Module.id.label("module_id"),
            Module.module_number.label("module_number"),
            Item.scanned_for_refile_queue.label("scanned_for_refile_queue"),
            ContainerType.type.label("container_type"),
            MediaType.name.label("media_type"),
            Owner.name.label("owner"),
            SizeClass.name.label("size_class"),
            Item.scanned_for_refile_queue_dt.label("scanned_for_refile_queue_dt"),
        )
        .select_from(Item)
        .join(Tray, Item.tray_id == Tray.id)
        .join(ContainerType, Tray.container_type_id == ContainerType.id)
        .join(ShelfPosition, Tray.shelf_position_id == ShelfPosition.id)
        .join(
            ShelfPositionNumber,
            ShelfPosition.shelf_position_number_id == ShelfPositionNumber.id,
        )
        .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
        .join(ShelfNumber, Shelf.shelf_number_id == ShelfNumber.id)
        .join(Ladder, Shelf.ladder_id == Ladder.id)
        .join(LadderNumber, Ladder.ladder_number_id == LadderNumber.id)
        .join(Side, Ladder.side_id == Side.id)
        .join(SideOrientation, Side.side_orientation_id == SideOrientation.id)
        .join(Aisle, Side.aisle_id == Aisle.id)
        .join(AisleNumber, Aisle.aisle_number_id == AisleNumber.id)
        .join(Module, Aisle.module_id == Module.id)
        .join(Building, Module.building_id == Building.id)
        .join(MediaType, Item.media_type_id == MediaType.id)
        .join(Barcode, Item.barcode_id == Barcode.id)
        .join(Owner, Item.owner_id == Owner.id)
        .join(SizeClass, Item.size_class_id == SizeClass.id)
        .filter(and_(*item_query_conditions))
    )

    # Base query for non-tray items
    non_tray_item_query = (
        select(
            NonTrayItem.id.label("id"),
            Barcode.value.label("barcode_value"),
            ShelfPosition.id.label("shelf_position_id"),
            ShelfPosition.location.label("location"),
            ShelfPosition.internal_location.label("internal_location"),
            ShelfPositionNumber.number.label("shelf_position_number"),
            ShelfPosition.shelf_id.label("shelf_id"),
            ShelfNumber.number.label("shelf_number"),
            Ladder.id.label("ladder_id"),
            LadderNumber.number.label("ladder_number"),
            Side.id.label("side_id"),
            SideOrientation.name.label("side_orientation"),
            Aisle.id.label("aisle_id"),
            AisleNumber.number.label("aisle_number"),
            Module.id.label("module_id"),
            Module.module_number.label("module_number"),
            NonTrayItem.scanned_for_refile_queue.label("scanned_for_refile_queue"),
            ContainerType.type.label("container_type"),
            MediaType.name.label("media_type"),
            Owner.name.label("owner"),
            SizeClass.name.label("size_class"),
            NonTrayItem.scanned_for_refile_queue_dt.label(
                "scanned_for_refile_queue_dt"
            ),
        )
        .select_from(NonTrayItem)
        .join(ShelfPosition, NonTrayItem.shelf_position_id == ShelfPosition.id)
        .join(
            ShelfPositionNumber,
            ShelfPosition.shelf_position_number_id == ShelfPositionNumber.id,
        )
        .join(ContainerType, NonTrayItem.container_type_id == ContainerType.id)
        .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
        .join(ShelfNumber, Shelf.shelf_number_id == ShelfNumber.id)
        .join(Ladder, Shelf.ladder_id == Ladder.id)
        .join(LadderNumber, Ladder.ladder_number_id == LadderNumber.id)
        .join(Side, Ladder.side_id == Side.id)
        .join(SideOrientation, Side.side_orientation_id == SideOrientation.id)
        .join(Aisle, Side.aisle_id == Aisle.id)
        .join(AisleNumber, Aisle.aisle_number_id == AisleNumber.id)
        .join(Module, Aisle.module_id == Module.id)
        .join(Building, Module.building_id == Building.id)
        .join(MediaType, NonTrayItem.media_type_id == MediaType.id)
        .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
        .join(Owner, NonTrayItem.owner_id == Owner.id)
        .join(SizeClass, NonTrayItem.size_class_id == SizeClass.id)
        .filter(and_(*non_tray_item_query_conditions))
    )

    # ✅ Correctly alias the subquery
    refile_queue = item_query.union_all(non_tray_item_query).alias("refile_queue")
    refile_queue = select(
        refile_queue.c.id,
        refile_queue.c.barcode_value,
        refile_queue.c.shelf_position_id,
        refile_queue.c.location,
        refile_queue.c.internal_location,
        refile_queue.c.shelf_position_number,
        refile_queue.c.shelf_id,
        refile_queue.c.shelf_number,
        refile_queue.c.ladder_id,
        refile_queue.c.ladder_number,
        refile_queue.c.side_id,
        refile_queue.c.side_orientation,
        refile_queue.c.aisle_id,
        refile_queue.c.aisle_number,
        refile_queue.c.module_id,
        refile_queue.c.module_number,
        refile_queue.c.scanned_for_refile_queue,
        refile_queue.c.container_type,
        refile_queue.c.media_type,
        refile_queue.c.owner,
        refile_queue.c.size_class,
        refile_queue.c.scanned_for_refile_queue_dt,
    ).select_from(refile_queue)

    return refile_queue


# Request Batch Upload Helper Functions
def _fetch_existing_data(session, model, values, column):
    return session.query(model).filter(column.in_(values)).all()


def _fetch_building_id_from_item(session, item_id, item_type):
    if item_type == "Item":
        item = session.query(Item).get(item_id)
        if item and item.tray:
            tray = item.tray
            if tray.shelf_position_id and tray.shelf_position:
                shelf_position = tray.shelf_position
                if shelf_position.shelf_id and shelf_position.shelf:
                    shelf = shelf_position.shelf
                    if shelf.ladder_id and shelf.ladder:
                        ladder = shelf.ladder
                        if ladder.side_id and ladder.side:
                            side = ladder.side
                            if side.aisle_id and side.aisle:
                                aisle = side.aisle
                                if aisle.module_id and aisle.module:
                                    module = aisle.module
                                    if module.building_id:
                                        return module.building_id
    else:
        non_tray_item = session.query(NonTrayItem).get(item_id)
        if (
            non_tray_item
            and non_tray_item.shelf_position_id
            and non_tray_item.shelf_position
        ):
            shelf_position = non_tray_item.shelf_position
            if shelf_position.shelf_id and shelf_position.shelf:
                shelf = shelf_position.shelf
                if shelf.ladder_id and shelf.ladder:
                    ladder = shelf.ladder
                    if ladder.side_id and ladder.side:
                        side = ladder.side
                        if side.aisle_id and side.aisle:
                            aisle = side.aisle
                            if aisle.module_id and aisle.module:
                                module = aisle.module
                                if module.building_id:
                                    return module.building_id


def _map_values_to_ids(data, key_column, value_column):
    return {getattr(item, key_column): getattr(item, value_column) for item in data}


def _validate_field(
    session, model, values, column, error_message, errors, request_data, field_name
):
    fetched_data = _fetch_existing_data(session, model, values, column)
    valid_values = {getattr(item, column.key) for item in fetched_data}
    errored_values = values - valid_values

    if errored_values:
        indices = request_data[request_data[field_name].isin(errored_values)].index
        for index in indices:
            barcode_value = request_data.at[index, "Item Barcode"]
            errors.append(
                {
                    "line": int(index) + 2,
                    "barcode_value": barcode_value,
                    "error": error_message
                }
            )
        return indices

    return set()


def _validate_items(session, items, request_data, errors):
    errored_indices = set()
    barcode_dict = _map_values_to_ids(items, "value", "id")
    barcode_values = set(request_data["Item Barcode"].astype(str))
    missing_barcodes = barcode_values - barcode_dict.keys()

    if missing_barcodes:
        for barcode in missing_barcodes:
            index = request_data[
                request_data["Item Barcode"].astype(str) == barcode
            ].index[0]
            errors.append(
                {
                    "line": int(index) + 2,
                    "barcode_value": barcode,
                    "error": f"""Item with Barcode {barcode} not found"""
                }
            )
            errored_indices.add(index)

    for barcode_value, barcode_id in barcode_dict.items():
        row_index = request_data[
            request_data["Item Barcode"].astype(str) == barcode_value
        ].index[0]
        item = session.query(Item).filter(Item.barcode_id == barcode_id).first()
        non_tray_item = (
            session.query(NonTrayItem)
            .filter(NonTrayItem.barcode_id == barcode_id)
            .first()
        )

        if item:
            _validate_item(
                session,
                item,
                row_index,
                barcode_value,
                errors,
                errored_indices,
                "Items",
            )
        elif non_tray_item:
            _validate_item(
                session,
                non_tray_item,
                row_index,
                barcode_value,
                errors,
                errored_indices,
                "Non tray item",
            )
        else:
            errors.append(
                {
                    "line": int(row_index) + 2,
                    "barcode_value": barcode_value,
                    "error": f"No items or non_trays found with barcode.",
                }
            )
            errored_indices.add(row_index)

    return errored_indices


def _validate_item(
    session, item, row_index, barcode_value, errors, errored_indices, item_type
):
    if item.status == "Out":
        errors.append(
            {
                "line": int(row_index) + 2,
                "barcode_value": barcode_value,
                "error": f"{item_type} {barcode_value} status is not shelved",
            }
        )
        errored_indices.add(row_index)
        return
    if item.status == "PickList":
        errors.append(
            {
                "line": int(row_index) + 2,
                "barcode_value": barcode_value,
                "error": f"{item_type} {barcode_value} is already in pick list and cannot be requested",
            }
        )
        errored_indices.add(row_index)
        return
    if item.status == "Withdrawn":
        errors.append(
            {
                "line": int(row_index) + 2,
                "barcode_value": barcode_value,
                "error": f"{item_type} {barcode_value} has already been withdrawn",
            }
        )
        errored_indices.add(row_index)
        return

    if item_type == "Items":
        existing_request = (
            session.query(Request)
            .filter(Request.item_id == item.id, Request.fulfilled == False)
            .first()
        )
    elif item_type == "Non tray item":
        existing_request = (
            session.query(Request)
            .filter(Request.non_tray_item_id == item.id, Request.fulfilled == False)
            .first()
        )

    if existing_request or item.status == "Requested":
        errors.append(
            {
                "line": int(row_index) + 2,
                "barcode_value": barcode_value,
                "error": f"{item_type} {barcode_value} is already requested",
            }
        )
        errored_indices.add(row_index)
        return

    if item_type == "Items":
        tray_id = item.tray_id
        shelf_position = _fetch_tray_shelf_position(session, tray_id)

        if (
            not shelf_position
            or not shelf_position.tray.scanned_for_shelving
            or not shelf_position.tray.shelf_position_id
        ):
            errors.append(
                {
                    "line": int(row_index) + 2,
                    "barcode_value": barcode_value,
                    "error": f"{item_type} {barcode_value} is not shelved",
                }
            )
            errored_indices.add(row_index)
    else:
        if not item.scanned_for_shelving or not item.shelf_position_id:
            errors.append(
                {
                    "line": int(row_index) + 2,
                    "barcode_value": barcode_value,
                    "error": f"{item_type} {barcode_value} is not shelved",
                }
            )
            errored_indices.add(row_index)


def _fetch_tray_shelf_position(session, tray_id):
    return session.query(ShelfPosition).join(Tray).filter(Tray.id == tray_id).first()


def _fetch_non_tray_shelf_position(session, shelf_position_id):
    return (
        session.query(ShelfPosition)
        .filter(ShelfPosition.id == shelf_position_id)
        .first()
    )


def validate_request_data(session, request_data: pd.DataFrame):
    errors = []
    barcodes_errored_indices = set()
    errored_indices = set()

    # Replace empty strings with NaN for External Request ID and check for missing values
    if (
        "External Request ID" not in request_data.columns
        or request_data["External Request ID"].replace("", pd.NA).isnull().any()
    ):
        missing_indices = request_data[
            request_data["External Request ID"].replace("", pd.NA).isnull()
        ].index
        for index in missing_indices:
            barcode_value = request_data.at[index, "Item Barcode"]
            errors.append(
                {
                    "line": int(index) + 2,
                    "barcode_value": barcode_value,
                    "error": "External Request ID is required"
                }
            )
            barcodes_errored_indices.update(missing_indices)
            errored_indices.update(missing_indices)

    # Replace empty strings with NaN and drop NaN values
    priority_values = set(request_data["Priority"].replace("", pd.NA).dropna().tolist())
    request_type_values = set(
        request_data["Request Type"].replace("", pd.NA).dropna().tolist()
    )
    delivery_location_values = set(
        request_data["Delivery Location"].replace("", pd.NA).dropna().tolist()
    )

    if priority_values:
        errored_indices.update(
            _validate_field(
                session,
                Priority,
                priority_values,
                Priority.value,
                "Priority not found",
                errors,
                request_data,
                "Priority",
            )
        )

    if request_type_values:
        errored_indices.update(
            _validate_field(
                session,
                RequestType,
                request_type_values,
                RequestType.type,
                "Request Type not found",
                errors,
                request_data,
                "Request Type",
            )
        )

    if delivery_location_values:
        errored_indices.update(
            _validate_field(
                session,
                DeliveryLocation,
                delivery_location_values,
                DeliveryLocation.name,
                "Delivery Location not found",
                errors,
                request_data,
                "Delivery Location",
            )
        )

    # Checking for duplicated "Item Barcode" rows as errors instead of dropping them
    duplicated_mask = request_data.duplicated(subset="Item Barcode")
    duplicate_indices = request_data[duplicated_mask].index

    for index in duplicate_indices:
        barcode_value = request_data.at[index, "Item Barcode"]
        errors.append(
            {
                "line": int(index) + 2,
                "barcode_value": str(barcode_value),
                "error": "Duplicate Item Barcode found"
            }
        )
        barcodes_errored_indices.add(index)
        errored_indices.add(index)

    barcodes = _fetch_existing_data(
        session,
        Barcode,
        request_data["Item Barcode"].astype(str).tolist(),
        Barcode.value,
    )

    barcodes_errored_indices.update(
        _validate_items(session, barcodes, request_data, errors)
    )
    errored_indices.update(barcodes_errored_indices)

    errored_indices = list(errored_indices)
    barcodes_errored_indices = list(barcodes_errored_indices)
    errored_df = request_data.loc[errored_indices]
    good_df = request_data.drop(index=barcodes_errored_indices)

    return good_df, errored_df, {"errors": errors}


def process_request_data(session, request_df: pd.DataFrame, batch_upload_id):
    building_id = None
    barcodes = _fetch_existing_data(
        session, Barcode, request_df["Item Barcode"].astype(str).tolist(), Barcode.value
    )
    barcode_dict = _map_values_to_ids(barcodes, "value", "id")
    items = _fetch_existing_data(session, Item, barcode_dict.values(), Item.barcode_id)
    non_tray_items = _fetch_existing_data(
        session, NonTrayItem, barcode_dict.values(), NonTrayItem.barcode_id
    )

    if items:
        items_ids = [item.id for item in items]
        session.query(Item).filter(Item.id.in_(items_ids)).update(
            {"status": "Requested"}, synchronize_session=False
        )
        session.commit()

    if non_tray_items:
        non_tray_items_ids = [item.id for item in non_tray_items]
        session.query(NonTrayItem).filter(
            NonTrayItem.id.in_(non_tray_items_ids)
        ).update({"status": "Requested"}, synchronize_session=False)
        session.commit()

    priorities = _fetch_existing_data(
        session, Priority, request_df["Priority"].tolist(), Priority.value
    )
    request_types = _fetch_existing_data(
        session, RequestType, request_df["Request Type"].tolist(), RequestType.type
    )
    delivery_locations = _fetch_existing_data(
        session,
        DeliveryLocation,
        request_df["Delivery Location"].tolist(),
        DeliveryLocation.name,
    )

    priority_dict = _map_values_to_ids(priorities, "value", "id")
    request_type_dict = _map_values_to_ids(request_types, "type", "id")
    delivery_location_dict = _map_values_to_ids(delivery_locations, "name", "id")

    item_dict = _map_values_to_ids(items, "barcode_id", "id")
    non_tray_item_dict = _map_values_to_ids(non_tray_items, "barcode_id", "id")

    request_df["priority_id"] = request_df["Priority"].map(priority_dict)
    request_df["request_type_id"] = request_df["Request Type"].map(request_type_dict)
    request_df["delivery_location_id"] = request_df["Delivery Location"].map(
        delivery_location_dict
    )
    request_df["barcode_id"] = request_df["Item Barcode"].astype(str).map(barcode_dict)
    request_df["item_id"] = request_df["barcode_id"].map(item_dict)
    request_df["non_tray_item_id"] = request_df["barcode_id"].map(non_tray_item_dict)

    request_df = request_df.drop(
        columns=["Priority", "Request Type", "Delivery Location", "Item Barcode"]
    )

    if building_id is None:
        for index, row in request_df.iterrows():
            if not pd.isnull(row["item_id"]):
                building_id = _fetch_building_id_from_item(
                    session, row["item_id"], "Item"
                )
                break
            if not pd.isnull(row["non_tray_item_id"]):
                building_id = _fetch_building_id_from_item(
                    session, row["non_tray_item_id"], "Non Tray Item"
                )
                break

    # Create Request instances from the DataFrame
    request_instances = []
    for index, row in request_df.iterrows():
        request_data = {
            "request_type_id": (
                row["request_type_id"]
                if not pd.isnull(row["request_type_id"])
                else None
            ),
            "item_id": row["item_id"] if not pd.isnull(row["item_id"]) else None,
            "non_tray_item_id": (
                row["non_tray_item_id"]
                if not pd.isnull(row["non_tray_item_id"])
                else None
            ),
            "delivery_location_id": (
                row["delivery_location_id"]
                if not pd.isnull(row["delivery_location_id"])
                else None
            ),
            "priority_id": (
                row["priority_id"] if not pd.isnull(row["priority_id"]) else None
            ),
            "external_request_id": (
                row["External Request ID"]
                if not pd.isnull(row["External Request ID"])
                else None
            ),
            "requestor_name": (
                row["Requestor Name"] if not pd.isnull(row["Requestor Name"]) else None
            ),
            "batch_upload_id": batch_upload_id,
        }
        if building_id is not None:
            request_data["building_id"] = building_id

        request_instances.append(Request(**request_data))

    return request_df, request_instances


# Withdraw Utilities
# Constants for statuses
INVALID_STATUSES = {"Requested", "Withdrawn"}
COMPLETED_STATUS = "Completed"


def _get_shelf_position(session: Session, tray_id: int):
    return session.query(ShelfPosition).join(Tray).filter(Tray.id == tray_id).first()


def _get_existing_withdrawals(session: Session, item_ids, item_type):
    model_map = {
        "Item": ItemWithdrawal,
        "NonTrayItem": NonTrayItemWithdrawal,
    }
    return (
        session.query(model_map[item_type])
        .filter(model_map[item_type].item_id.in_(item_ids))
        .all()
    )


def _validate_withdraw_job_existing_item(existing_withdraws, job_id, status):
    return any(
        item.id != job_id and item.status != status for item in existing_withdraws
    )


def _validate_item_status(item, index, errors, error_message):
    if item.status in INVALID_STATUSES:
        errors.append({"line": int(index), "error": error_message})


def validate_item_not_shelved(shelf_position):
    if not shelf_position or not shelf_position.tray.scanned_for_shelving:
        return True
    return False


def validate_container_not_shelved(item):
    if not item or not item.shelf_position_id or not item.scanned_for_shelving:
        return True
    return False


def _validate_withdraw_item(session, item, withdraw_job_id, barcode, index, errors):
    item_errors = []

    _validate_item_status(
        item, index, item_errors, "Item must have status of ['In', 'Out']"
    )
    shelf_position = (
        session.query(ShelfPosition).join(Tray).filter(Tray.id == item.tray_id).first()
    )
    if validate_item_not_shelved(shelf_position):
        errors.append({"line": int(index), "error": "Item is not shelved"})
    existing_withdrawals = (
        session.query(WithdrawJob)
        .join(ItemWithdrawal, WithdrawJob.id == ItemWithdrawal.withdraw_job_id)
        .filter(ItemWithdrawal.item_id == item.id)
        .all()
    )
    if _validate_withdraw_job_existing_item(
        existing_withdrawals, withdraw_job_id, "Completed"
    ):
        item_errors.append(
            {"line": int(index), "error": "Item is in existing withdraw job"}
        )

    if not item_errors:
        return (
            ItemWithdrawal(item_id=item.id, withdraw_job_id=withdraw_job_id),
            item_errors,
        )
    else:
        errors.extend(item_errors)
        return None, item_errors


def process_withdraw_job_data(
    session: Session, withdraw_job_id: int, barcodes: List, df: pd.DataFrame
) -> Tuple[List, List, List, Dict]:
    errors = []
    withdraw_items = []
    withdraw_non_tray_items = []
    withdraw_trays = []
    update_dt = datetime.now(timezone.utc)

    # Collect all barcode ids
    barcode_ids = [barcode.id for barcode in barcodes]

    # Fetch all necessary data in batch
    items = {
        item.barcode_id: item
        for item in session.query(Item).filter(Item.barcode_id.in_(barcode_ids)).all()
    }
    non_tray_items = {
        non_tray_item.barcode_id: non_tray_item
        for non_tray_item in session.query(NonTrayItem)
        .filter(NonTrayItem.barcode_id.in_(barcode_ids))
        .all()
    }

    # Fetch existing withdrawals in one batch query
    existing_withdrawals = {
        non_tray_item_id: withdraw_job_id
        for non_tray_item_id, withdraw_job_id in session.query(
            NonTrayItemWithdrawal.non_tray_item_id,
            NonTrayItemWithdrawal.withdraw_job_id,
        )
        .filter(
            NonTrayItemWithdrawal.non_tray_item_id.in_(
                [item.id for item in non_tray_items.values()]  # Extract `id` values
            )
        )
        .all()
    }

    # Use a set for duplicate checks in withdraw_trays
    withdraw_tray_set = {(tw.tray_id, tw.withdraw_job_id) for tw in withdraw_trays}

    # Create a lookup dictionary for barcodes in the DataFrame for retrieval
    barcode_to_index = {
        str(value): idx for idx, value in enumerate(df["Item Barcode"].astype(str))
    }

    for barcode in barcodes:
        item = items.get(barcode.id)
        non_tray_item = non_tray_items.get(barcode.id)

        # Get the index from preprocessed barcode_to_index dictionary
        index = barcode_to_index.get(str(barcode.value), None)
        if index is None:
            errors.append({"error": f"Barcode {barcode.value} not found"})
            continue

        if item:
            item_withdrawal, item_errors = _validate_withdraw_item(
                session, item, withdraw_job_id, barcode, index + 1, errors
            )
            if item_withdrawal:
                withdraw_items.append(item_withdrawal)
                new_tray_withdrawal = TrayWithdrawal(
                    tray_id=item.tray_id, withdraw_job_id=withdraw_job_id
                )

                # Check if the tray_id and withdraw_job_id already exist in withdraw_trays
                # Use a set for faster lookup instead of `any()`
                if (
                    new_tray_withdrawal.tray_id,
                    new_tray_withdrawal.withdraw_job_id,
                ) not in withdraw_tray_set:
                    withdraw_tray_set.add(
                        (
                            new_tray_withdrawal.tray_id,
                            new_tray_withdrawal.withdraw_job_id,
                        )
                    )
                    withdraw_trays.append(new_tray_withdrawal)

                item.update_dt = update_dt
                session.add(item)
        elif non_tray_item:
            _validate_item_status(
                non_tray_item,
                index + 1,
                errors,
                "Non Tray Item must have status of ['In', 'Out']",
            )
            if existing_withdrawals.get(non_tray_item.id) == withdraw_job_id:
                errors.append(
                    {
                        "line": int(index) + 2,
                        "error": "Non Tray Item is in existing withdraw job",
                    }
                )
            elif validate_container_not_shelved(non_tray_item):
                errors.append(
                    {"line": int(index) + 2, "error": "Non Tray Item is not shelved"}
                )
            else:
                withdraw_non_tray_items.append(
                    NonTrayItemWithdrawal(
                        non_tray_item_id=non_tray_item.id,
                        withdraw_job_id=withdraw_job_id,
                    )
                )
                non_tray_item.update_dt = update_dt
                session.add(non_tray_item)
        else:
            errors.append({"line": int(index) + 2, "error": "Barcode not found"})

    return withdraw_items, withdraw_non_tray_items, withdraw_trays, {"errors": errors}


async def start_session_with_user_id(audit_name: str, session):
    """
    This method is to add the user id for any database change.
    """
    session.execute(text(f"select set_config('audit.user_id', '{audit_name}', true)"))


async def set_session_to_request(
    request: Request,
    session: Session,
    audit_name: str,
):
    if request.method != "GET":
        request.state.db_session = session

        await start_session_with_user_id(audit_name, session=request.state.db_session)

    return request
    # if request.method != "GET":
    #     with session_manager() as session:
    #         request.state.db_session = session
    #         session.exec(text(f"select set_config('audit.user_id', '{user_email}', true)"))
    #         # await start_session_with_user_id(user_email, session=session)  # Explicitly pass session
    # return request


def get_sortable_fields(model):
    """
    Dynamically retrieves all column names from the SQLAlchemy model.
    """
    return {column.key for column in inspect(model).c}


def get_sorted_query(model, query, sort_params):
    """
    Sorts the query based on the provided sort parameters.
    """
    if sort_params.sort_order not in ["asc", "desc"]:
        raise BadRequest(
            detail=f"Invalid value for ‘sort_order'. Allowed values are: ‘asc’, ‘desc’",
        )

    sortable_fields = get_sortable_fields(model)
    if sort_params.sort_by not in sortable_fields:
        if sort_params.sort_order == "asc":
            if sort_params.sort_by == "request_type":
                query = query.join(RequestType).order_by(asc(RequestType.name))
            if sort_params.sort_by == "barcode_value":
                query = query.join(Barcode).order_by(asc(Barcode.value))
            if sort_params.sort_by == "building_name":
                query = query.join(Building).order_by(asc(Building.name))
            if sort_params.sort_by == "priority":
                query = query.join(Priority).order_by(asc(Priority.name))
            if sort_params.sort_by == "media_type":
                query = query.join(MediaType).order_by(asc(MediaType.name))
            if sort_params.sort_by == "delivery_location":
                query = query.join(DeliveryLocation).order_by(
                    asc(DeliveryLocation.name)
                )
            if sort_params.sort_by == "owner":
                query = query.join(Owner).order_by(asc(Owner.name))
            if sort_params.sort_by == "size_class":
                query = query.join(SizeClass).order_by(asc(SizeClass.name))
            if sort_params.sort_by == "size_class_short_name":
                query = query.join(SizeClass).order_by(asc(SizeClass.short_name))
            if sort_params.sort_by == "shelf_type":
                query = query.join(ShelfType).order_by(asc(ShelfType.type))
            if sort_params.sort_by == "container_type":
                query = query.join(ContainerType).order_by(asc(ContainerType.type))
            if sort_params.sort_by == "request_count":
                query = query.join(Request).order_by(asc(func.count(Request.id)))
        else:
            if sort_params.sort_by == "request_type":
                query = query.join(RequestType).order_by(desc(RequestType.name))
            if sort_params.sort_by == "barcode_value":
                query = query.join(Barcode).order_by(desc(Barcode.value))
            if sort_params.sort_by == "building_name":
                query = query.join(Building).order_by(desc(Building.name))
            if sort_params.sort_by == "priority":
                query = query.join(Priority).order_by(desc(Priority.name))
            if sort_params.sort_by == "media_type":
                query = query.join(MediaType).order_by(desc(MediaType.name))
            if sort_params.sort_by == "delivery_location":
                query = query.join(DeliveryLocation).order_by(
                    desc(DeliveryLocation.name)
                )
            if sort_params.sort_by == "owner":
                query = query.join(Owner).order_by(desc(Owner.name))
            if sort_params.sort_by == "size_class":
                query = query.join(SizeClass).order_by(desc(SizeClass.name))
            if sort_params.sort_by == "size_class_short_name":
                query = query.join(SizeClass).order_by(desc(SizeClass.short_name))
            if sort_params.sort_by == "shelf_type":
                query = query.join(ShelfType).order_by(desc(ShelfType.type))
            if sort_params.sort_by == "container_type":
                query = query.join(ContainerType).order_by(desc(ContainerType.type))
            if sort_params.sort_by == "request_count":
                query = query.join(Request).order_by(desc(func.count(Request.id)))

    elif sort_params.sort_by in sortable_fields:
        sort_field = getattr(model, sort_params.sort_by, None)
        if sort_field:
            if sort_params.sort_order == "asc":
                query = query.order_by(asc(sort_field))
            else:
                query = query.order_by(desc(sort_field))
    else:
        raise BadRequest(
            detail=f"Invalid sort parameter: {sort_params.sort_by}",
        )

    return query


def is_tz_naive(dt: datetime) -> bool:
    """Checks if a date is timezone naive"""
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None
