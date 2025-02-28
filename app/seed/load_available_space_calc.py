import os, csv

from collections import defaultdict
from app.database.session import get_sqlalchemy_session
from app.logger import migration_logger
from concurrent.futures import as_completed, ThreadPoolExecutor

from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem

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


def worker_calc_shelf_space(shelf_id, index, total_shelves):
    """Execution worker for parallel shelf space calc"""
    session = next(get_sqlalchemy_session())
    migration_logger.info(f"Calculating space: {index + 1}/{total_shelves}")

    try:
        shelf = session.get(Shelf, shelf_id)
        shelf.calc_available_space(session=session)
        session.add(shelf)
        session.commit()
        shelf_result = [1, 0, None]
    except Exception as e:
        migration_logger.info(f"ERROR on shelf_id {shelf_id} - {e}")
        shelf_result = [
            0,
            1,
            {
                "row": shelf.id,
                "reason": f"{e}"
            }
        ]
        session.rollback()
    session.close()

    return shelf_result


def load_available_space_calc():
    """
    Parallel processing that updates the shelf.available_space
    stored value on all Shelves in the database.
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
    shelf_queryset = (session.query(Shelf).all())
    total_shelves = session.query(Shelf).count()
    shelf_ids = [shelf.id for shelf in shelf_queryset]
    session.close()

    with ThreadPoolExecutor(max_workers=40) as executor:
        futures = [
            executor.submit(
                worker_calc_shelf_space,
                shelf_id,
                index,
                total_shelves
            )
            for index, shelf_id in enumerate(shelf_ids)
        ]

        # Collect and unpack results
        for future in as_completed(futures):
            p_shelf_result = future.result()
            if p_shelf_result:
                results["shelves"]["successful_rows"] += p_shelf_result[0]
                results["shelves"]["failed_rows"] += p_shelf_result[1]
                if p_shelf_result[2]:
                    results["shelves"]["errors"].append(p_shelf_result[2])

    # Gen error files
    generate_seed_error_report("available_space_errors.csv", results["shelves"]["errors"])

    # Summary Result
    migration_logger.info("======SHELF SPACE CALC COMPLETE======")
    # Section Results
    migration_logger.info(
        f"Successfully processed {results['shelves']['successful_rows']} rows"
    )
    migration_logger.info(
        f"Failed to process {results['shelves']['failed_rows']} rows"
    )
    migration_logger.info(f"Failed data output to available_space_errors.csv")
