import os, csv

from collections import defaultdict
from concurrent.futures import as_completed, ThreadPoolExecutor

from app.database.session import get_sqlalchemy_session
from app.logger import migration_logger
from app.seed.scripts.load_tray import load_tray

from app.models.container_types import ContainerType
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.size_class import SizeClass
from app.models.owners import Owner
from app.models.media_types import MediaType
from app.models.barcodes import Barcode
from app.models.barcode_types import BarcodeType
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf

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


def chunked_reader(legacy_tray_path, chunk_size=1000):
    with open(
        legacy_tray_path,
        mode="r",
        newline="",
        encoding="utf-8"
    ) as file:
        reader = csv.reader(file)
        chunk = []
        for row in reader:
            chunk.append(row)
            if len(chunk) == chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk


def process_container_row(
        row_num,
        row,
        container_types_dict,
        shelf_position_dict,
        size_class_dict,
        owners_dict,
        media_types_dict,
        barcode_types_dict
):
    """
    Worker processor for individual rows
    Returns a collection of results for main thread.

    (
        int: skipped_row_count,
        list: tray_result
    )
    """
    session = next(get_sqlalchemy_session())
    migration_logger.info(f"PROCESSING tray.txt ROW: {row_num}")
    skipped_row_count = 0

    container_type = None

    # Determine container type
    container_barcode = row[0]

    if container_barcode[0] == 'T':
        container_type = 'Non-Tray' # Ironic, I know.
    else:
        container_type = 'Tray'

    # Field handoff
    media_type = row[2]
    shelf_barcode_value = row[4]
    owner_name = row[7]
    accession_dt = row[8]
    shelved_dt = row[9]
    size_class_short_name = row[10]
    shelf_position_number = row[18]

    if container_type == 'Tray':
        tray_result = load_tray(
            row_num,
            container_barcode,
            media_type,
            shelf_barcode_value,
            owner_name,
            accession_dt,
            shelved_dt,
            size_class_short_name,
            shelf_position_number,
            session,
            container_types_dict,
            shelf_position_dict,
            size_class_dict,
            owners_dict,
            media_types_dict,
            barcode_types_dict
        )
    else:
        skipped_row_count = 1
        tray_result = [0, 0, None]
    session.close()
    return (
        skipped_row_count,
        tray_result
    )


def load_containers():
    """
    Parallel Migration Processing on LAS Container Data

    Ingests Trays And NonTrayItems from a tray.txt (csv)

    Column indices are 0-based
    """
    legacy_tray_path = os.path.join(
        current_dir, "legacy_snapshot", "tray.txt"
    )

    # tracks pre-skip based on csv data, not skip due to processing
    skipped_row_count = 0

    results = {
        'trays': {
            'successful_rows': 0,
            'failed_rows': 0,
            'errors': []
        }
    }

    #Re-usable static dict querysets to pass through for worker execution
    session = next(get_sqlalchemy_session())
    container_types_dict = {
        ct.type: ct.id for ct in session.query(ContainerType).all()
    }
    size_class_dict = {
        sc.short_name: sc.id for sc in session.query(SizeClass).all()
    }
    owners_dict = {
        o.name: o.id for o in session.query(Owner).all()
    }
    media_types_dict = {
        mt.name: mt.id for mt in session.query(MediaType).all()
    }
    barcode_types_dict = {
        bct.name: bct.id for bct in session.query(BarcodeType).all()
    }
    sp_lookup_query = (
        session.query(
            Barcode.value.label('shelf_barcode_value'),
            ShelfPosition.id.label('shelf_position_id'),
            ShelfPositionNumber.number.label('shelf_position_number_value'),
        )
        .join(Shelf, Shelf.barcode_id == Barcode.id)
        .join(ShelfPosition, ShelfPosition.shelf_id == Shelf.id)
        .join(ShelfPositionNumber, ShelfPositionNumber.id == ShelfPosition.shelf_position_number_id)
        .all()
    )
    shelf_position_dict = defaultdict(list)
    for row in sp_lookup_query:
        shelf_position_dict[row.shelf_barcode_value].append(
            {row.shelf_position_number_value: row.shelf_position_id}
        )
    # Convert to a regular dictionary
    shelf_position_dict = dict(shelf_position_dict)
    session.close()

    with ThreadPoolExecutor(max_workers=16) as executor:
        for chunk_start, chunk in enumerate(chunked_reader(legacy_tray_path, chunk_size=80000), start=1):

            # DO NOT REMOVE (until this is handled by params)
            # 619k rows in 80k chunks,  8 chunks
            # (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8)
            # each run will overwrite previous error file
            # so extract it between runs. also rebuild app between runs
            # in order to capture chunk selection changes
            # if chunk_start < 1:
            #     continue
            # if chunk_start > 1:
            #     break

            futures = [
                executor.submit(
                    process_container_row,
                    row_num,
                    row,
                    container_types_dict,
                    shelf_position_dict,
                    size_class_dict,
                    owners_dict,
                    media_types_dict,
                    barcode_types_dict
                )
                for row_num, row in enumerate(chunk, start=(chunk_start - 1) * 1000 + 1)
            ]

            # Collect and unpack results
            for future in as_completed(futures):
                p_skipped_row_count, p_tray_result = future.result()
                skipped_row_count += p_skipped_row_count
                if p_tray_result:
                    results["trays"]["successful_rows"] += p_tray_result[0]
                    results["trays"]["failed_rows"] += p_tray_result[1]
                    if p_tray_result[2]:
                        results["trays"]["errors"].append(p_tray_result[2])

    # Gen error files
    generate_seed_error_report("tray_tray_errors.csv", results["trays"]["errors"])

    # Summary Result
    migration_logger.info("======Container INGEST COMPLETE======")
    # migration_logger.info(f"rows: {row_num}, rows skipped: {skipped_row_count}")
    migration_logger.info(f"rows skipped: {skipped_row_count}")
    # Section Results
    migration_logger.info("====TRAY RESULTS====")
    migration_logger.info(
        f"Successfully processed {results['trays']['successful_rows']} rows"
    )
    migration_logger.info(
        f"Failed to process {results['trays']['failed_rows']} rows"
    )
    migration_logger.info(f"Failed data output to tray_tray_errors.csv")
