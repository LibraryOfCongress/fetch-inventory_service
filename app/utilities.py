from sqlalchemy import select, and_
from sqlalchemy.orm import join

from app.config.exceptions import NotFound
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.buildings import Building
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.ladders import Ladder
from app.models.shelves import Shelf
from app.models.shelf_positions import ShelfPosition


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
    ladder_id
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
    available_shelf_positions = session.exec(shelf_position_query.where(and_(*conditions)))

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
        available_positions_for_size = [position for position in available_shelf_positions if position.Shelf.size_class_id == container_object.size_class_id]

        if not available_positions_for_size:
            raise NotFound(
                detail=f"No available positions on shelves at size class {container_object.size_class_id} needed for container with barcode {container_object.barcode.value}"
            )

        # get matching owner options
        available_positions_for_owner = [position for position in available_positions_for_size if position.Shelf.owner_id == container_object.owner_id]

        if not available_positions_for_owner:
            raise NotFound(
                detail=f"No available positions on shelves for owner id {container_object.owner_id} at size class {container_object.size_class_id} needed for container with barcode {container_object.barcode.value}"
            )

        # both actual and proposed get set
        container_object.shelf_position_id = available_positions_for_owner[0].ShelfPosition.id
        container_object.shelf_position_proposed_id = available_positions_for_owner[0].ShelfPosition.id

        # Remove reserved position from available before next iteration
        available_shelf_positions = [position for position in available_shelf_positions if position.ShelfPosition.id != container_object.shelf_position_id]

        session.add(container_object)

    # Commit transactions at the end, in case of errors
    session.commit()

    return
