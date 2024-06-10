import pytz
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.config.exceptions import NotFound
from app.logger import inventory_logger
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.ladders import Ladder
from app.models.shelves import Shelf
from app.models.shelf_positions import ShelfPosition


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

    return {"aisle": aisle, "ladder": ladder, "shelf": shelf}


def process_containers_for_shelving(
    session,
    container_type,
    containers,
    shelving_job_id,
    building_id,
    shelve_on_building,
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
    # query is built without execution beforehand
    shelf_position_query = select(ShelfPosition, Shelf).join(Shelf)
    conditions = []

    # constrain to empty shelf positions
    conditions.append(ShelfPosition.tray == None)
    conditions.append(ShelfPosition.non_tray_item == None)

    # perform joins from most constrained to least, for efficiency
    if ladder_id:
        conditions.append(Shelf.ladder_id == ladder_id)
    elif side_id:
        # join till this point
        conditions.append(Shelf.ladder_id == Ladder.id)

        conditions.append(Ladder.side_id == side_id)
    elif aisle_id:
        # join till this point
        conditions.append(Shelf.ladder_id == Ladder.id)
        conditions.append(Ladder.side_id == Side.id)

        conditions.append(Side.aisle_id == aisle_id)
    elif module_id:
        # join till this point
        conditions.append(Shelf.ladder_id == Ladder.id)
        conditions.append(Ladder.side_id == Side.id)
        conditions.append(Side.aisle_id == Aisle.id)

        conditions.append(Aisle.module_id == module_id)
    else:
        # join till this point
        conditions.append(Shelf.ladder_id == Ladder.id)
        conditions.append(Ladder.side_id == Side.id)
        conditions.append(Side.aisle_id == Aisle.id)

        if shelve_on_building:
            # search in aisles belonging to a building
            conditions.append(Aisle.building_id == building_id)
        else:
            # searching in aisles belonging to a building's modules
            conditions.append(Aisle.module_id == Module.id)
            conditions.append(Module.building_id == building_id)

    # Execute the query and fetch the results
    # keep in mind this is a joined list of [(ShelfPosition, Shelf)]
    available_shelf_positions = session.exec(
        shelf_position_query.where(and_(*conditions))
    )

    # convert ChunkedIterator for list comprehension
    available_shelf_positions = list(available_shelf_positions)

    if not available_shelf_positions:
        raise NotFound(detail=f"No available shelf positions within constraints.")

    # process containers
    for container_object in containers:
        # assign container to shelving job
        container_object.shelving_job_id = shelving_job_id

        # If container already shelved (from previous job attempt), skip
        if container_object.shelf_position_id:
            continue

        # get matching size_class options
        available_positions_for_size = [
            position
            for position in available_shelf_positions
            if position.Shelf.size_class_id == container_object.size_class_id
        ]

        if not available_positions_for_size:
            raise NotFound(
                detail=f"No available positions on shelves at size class {container_object.size_class_id} needed for container with barcode {container_object.barcode.value}"
            )

        # get matching owner options
        available_positions_for_owner = [
            position
            for position in available_positions_for_size
            if position.Shelf.owner_id == container_object.owner_id
        ]

        if not available_positions_for_owner:
            raise NotFound(
                detail=f"No available positions on shelves for owner id {container_object.owner_id} at size class {container_object.size_class_id} needed for container with barcode {container_object.barcode.value}"
            )

        # both actual and proposed get set
        container_object.shelf_position_id = available_positions_for_owner[
            0
        ].ShelfPosition.id
        container_object.shelf_position_proposed_id = available_positions_for_owner[
            0
        ].ShelfPosition.id

        # Remove reserved position from available before next iteration
        available_shelf_positions = [
            position
            for position in available_shelf_positions
            if position.ShelfPosition.id != container_object.shelf_position_id
        ]

        session.add(container_object)

    # Commit transactions at the end, in case of errors
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
    if original_record.last_transition:
        last_transition = make_aware(original_record.last_transition)
        original_record.run_time += run_timestamp - last_transition
    else:
        create_dt = make_aware(original_record.create_dt)
        original_record.run_time += run_timestamp - create_dt

    original_record.last_transition = run_timestamp

    return original_record
