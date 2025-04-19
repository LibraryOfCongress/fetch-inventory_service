import os, csv, gc

from app.database.session import get_sqlalchemy_session, get_sqlalchemy_session_thread_safe
from app.logger import migration_logger
from sqlalchemy.orm import selectinload, joinedload
from concurrent.futures import as_completed, ThreadPoolExecutor
from app.models.shelves import Shelf
from app.models.shelf_positions import ShelfPosition
from app.models.ladders import Ladder
from app.models.sides import Side
from app.models.modules import Module
from app.models.aisles import Aisle


current_dir = os.path.dirname(os.path.abspath(__file__))


def generate_seed_error_report(output_file, errors):
    """
    Collects error rows from processing
    and creates a csv report

    Params
      - output_file - file name to create
      - errors - list of errors
    """
    error_directory = "errors"

    # Ensure the directory exists
    os.makedirs(
        os.path.join(current_dir, error_directory),
        exist_ok=True
    )

    output_file = os.path.join(
        current_dir,
        error_directory,
        output_file
    )

    # only gen file if there are errors
    if len(errors) > 0:
        with open(output_file, mode="w", newline="") as error_file:
            # report headers from first error
            writer = csv.DictWriter(error_file, fieldnames=errors[0].keys())
            writer.writeheader()
            writer.writerows(errors)

    return


# def worker_calc_shelf_location(shelf_id, index, total_shelves):
def worker_calc_shelf_location(shelf, index, total_shelves):
    """
    Threadpool worker to Calc a shelf's 
    location strings, and
    the associated shelf position strings
    """
    # session = get_sqlalchemy_session_thread_safe()
    migration_logger.info(f"Updating address: {index + 1}/{total_shelves}")

    updated_shelf = None
    updated_shelf_positions = []

    try:
        # shelf = session.get(Shelf, shelf_id)
        shelf.update_shelf_address()

        for position in shelf.shelf_positions:
            position.update_position_address()
            # session.add(position)
            updated_shelf_positions.append(position)

        # session.add(shelf)
        updated_shelf = shelf
        # session.commit()
        result = [1, 0, None, updated_shelf, updated_shelf_positions]
    except Exception as e:
        # migration_logger.error(f"ERROR on shelf_id {shelf_id} - {e}")
        migration_logger.error(f"ERROR on shelf_id {shelf} - {e}")
        # session.rollback()
        result = [
            0,
            1,
            {
                "row": shelf,
                "reason": f"{e}"
            },
            None,
            []
        ]
    # finally:
        # session.close()


    return result


def load_addressing():
    """
    Parallel processing that generates
    shelf and shelf position addressing
    across the existing system.
    """
    session = next(get_sqlalchemy_session())

    results = {
        'shelves': {
            'successful_rows': 0,
            'failed_rows': 0,
            'errors': []
        }
    }

    # query all shelves
    total_shelves = session.query(Shelf).count()

    shelves = (
        session.query(Shelf)
        .options(
            joinedload(Shelf.shelf_number),
            joinedload(Shelf.shelf_positions)
                .joinedload(ShelfPosition.shelf),
            joinedload(Shelf.shelf_positions)
                .joinedload(ShelfPosition.shelf_position_number),
            joinedload(Shelf.ladder)
                .joinedload(Ladder.ladder_number),
            joinedload(Shelf.ladder)
                .joinedload(Ladder.side)
                .joinedload(Side.side_orientation),
            joinedload(Shelf.ladder)
                .joinedload(Ladder.side)
                .joinedload(Side.aisle)
                .joinedload(Aisle.aisle_number),
            joinedload(Shelf.ladder)
                .joinedload(Ladder.side)
                .joinedload(Side.aisle)
                .joinedload(Aisle.module)
                .joinedload(Module.building),
        )
        .all()
    )

    session.close()

    with ThreadPoolExecutor(max_workers=40) as executor:

        session = next(get_sqlalchemy_session())

        futures = [
            executor.submit(
                worker_calc_shelf_location,
                # shelf_id,
                shelf,
                index,
                total_shelves
            )
            # for index, shelf_id in enumerate(shelf_ids)
            for index, shelf in enumerate(shelves)
        ]

        shelves_to_update = []
        shelf_positions_to_update = []

        # Collect and unpack results
        for future in as_completed(futures):
            p_shelf_result = future.result()
            if p_shelf_result:
                results["shelves"]["successful_rows"] += p_shelf_result[0]
                results["shelves"]["failed_rows"] += p_shelf_result[1]
                if p_shelf_result[2]:
                    results["shelves"]["errors"].append(p_shelf_result[2])
                if p_shelf_result[3]:
                    shelves_to_update.append(p_shelf_result[3])
                    shelf_positions_to_update.extend(p_shelf_result[4])

        session.bulk_save_objects(shelves_to_update, return_defaults=True)
        session.bulk_save_objects(shelf_positions_to_update, return_defaults=True)
        session.commit()
        # Clear resources
        session.close()
        gc.collect()

    # Gen error files
    generate_seed_error_report("addressing_errors.csv", results["shelves"]["errors"])

    # Summary Result
    migration_logger.info("======SHELF ADDRESS GEN COMPLETE======")
    # Section Results
    migration_logger.info(
        f"Successfully processed {results['shelves']['successful_rows']} rows"
    )
    migration_logger.info(
        f"Failed to process {results['shelves']['failed_rows']} rows"
    )
    migration_logger.info(f"Failed data output to addressing_errors.csv")

    return
