import os, csv, gc

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from app.database.session import get_sqlalchemy_session, get_sqlalchemy_session_for_storage_migration
from app.logger import migration_logger
from app.seed.scripts.load_side import load_side
from app.seed.scripts.load_ladder import load_ladder
from app.seed.scripts.load_shelf import load_shelf
from app.seed.scripts.load_shelf_positions import load_shelf_positions

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

    if output_file == "loc_shelf_position_errors.csv":
        # only gen file if there are errors
        # shelf position is a list of error lists, treat differently
        if len(errors) > 0:
            with open(output_file, mode="w", newline="") as error_file:
                writer = csv.DictWriter(error_file, fieldnames=errors[0][0].keys())
                writer.writeheader()
                for error_list in errors:
                    writer.writerows(error_list)
    else:
    # only gen file if there are errors
        if len(errors) > 0:
            with open(output_file, mode="w", newline="") as error_file:
                # report headers from first error
                writer = csv.DictWriter(error_file, fieldnames=errors[0].keys())
                writer.writeheader()
                writer.writerows(errors)

    return


def chunked_reader(legacy_location_path, chunk_size=1000):
    with open(
        legacy_location_path,
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


def process_loc_row(
        row_num,
        row,
        side_orientations_dict,
        ladder_number_dict,
        shelf_number_dict,
        container_type_dict,
        owners_dict,
        shelf_position_number_dict,
        shelf_type_max_cap_dict,
        barcode_types_dict,
        shelf_type_lookup_dict,
        aisle_dict
):
    """
    Worker processor for individual rows
    Returns a collection of results for main thread.

    (
        int: skipped_row_count,
        list: side_result,
        list: ladder_result,
        list: shelf_result,
        list: shelf_position_result
    )
    """
    # session = next(get_sqlalchemy_session())
    session = get_sqlalchemy_session_for_storage_migration()
    migration_logger.info(f"PROCESSING loc.txt ROW: {row_num}")
    skipped_row_count = 0

    # SIDES
    side_orientation = row[1].upper()
    aisle_number = row[11]

    # business logic
    if aisle_number in {"99", "370"} or (499 < int(aisle_number) < 600):
        skipped_row_count += 1
        session.close()
        return (
            skipped_row_count,
            None,
            None,
            None,
            None
        )

    side_result = load_side(
        side_orientation,
        aisle_number,
        row_num,
        session,
        side_orientations_dict,
        aisle_dict
    )

    if not side_result[4]:
        # skip remaining processing for row
        # this keeps errors categorized and saves time
        session.close()
        return (
            skipped_row_count,
            side_result,
            None,
            None,
            None
        )

    # LADDERS
    ladder_number = row[2]
    current_side_id = side_result[4]

    # business logic
    if ladder_number in {"96", "81"}:
        session.close()
        return (
            skipped_row_count,
            side_result,
            None,
            None,
            None
        )

    ladder_result = load_ladder(
        ladder_number,
        current_side_id,
        row_num,
        session,
        ladder_number_dict
    )

    if not ladder_result[4]:
        # skip remaining processing for row
        # this keeps errors categorized and saves time
        session.close()
        return (
            skipped_row_count,
            side_result,
            ladder_result,
            None,
            None
        )


    # SHELVES
    shelf_number = row[7]
    current_ladder_id = ladder_result[4]
    owner_name = row[4]
    shelf_height = row[9]
    shelf_width = row[13]
    shelf_depth = row[12]
    shelf_legacy_type = row[6]
    shelf_barcode_value = row[10]
    shelf_new_type = row[24]
    shelf_container_type = row[25]

    shelf_result = load_shelf(
        shelf_number,
        current_ladder_id,
        owner_name,
        shelf_height,
        shelf_width,
        shelf_depth,
        shelf_legacy_type,
        shelf_barcode_value,
        shelf_new_type,
        shelf_container_type,
        row_num,
        session,
        shelf_number_dict,
        container_type_dict,
        owners_dict,
        barcode_types_dict,
        shelf_type_lookup_dict
    )

    if not shelf_result[4]:
        # skip remaining processing for row
        # this keeps errors categorized and saves time
        session.close()
        return (
            skipped_row_count,
            side_result,
            ladder_result,
            shelf_result,
            None
        )


    # SHELF POSITIONS
    current_shelf_id = shelf_result[4]
    current_shelf_type_id = shelf_result[5]

    shelf_position_result = load_shelf_positions(
        current_shelf_id,
        current_shelf_type_id,
        row_num,
        session,
        shelf_position_number_dict,
        shelf_type_max_cap_dict
    )

    session.close()
    return (
        skipped_row_count,
        side_result,
        ladder_result,
        shelf_result,
        shelf_position_result
    )


def load_storage_locations():
    """
    Parallel Migration Processing on LAS Location Data

    Determine and load unique sides, ladders,
    and shelves from loc.txt (csv)

    Column indices are 0-based
    """
    legacy_location_path = os.path.join(
        current_dir, "legacy_snapshot", "loc.txt"
    )

    # tracks pre-skip based on csv data, not skip due to processing
    skipped_row_count = 0

    results = {
        'sides': {
            'successful_rows': 0,
            'failed_rows': 0,
            'errors': [],
            'new_record_count': 0
        },
        'ladders': {
            'successful_rows': 0,
            'failed_rows': 0,
            'errors': [],
            'new_record_count': 0
        },
        'shelves': {
            'successful_rows': 0,
            'failed_rows': 0,
            'errors': [],
            'new_record_count': 0
        },
        'shelf_positions': {
            'successful_rows': 0,
            'failed_rows': 0,
            'errors_list': [], # handle diff in csv gen
            'new_record_count': 0,
            'failed_record_count': 0
        }
    }

    # reusable memory dicts
    from app.models.side_orientations import SideOrientation
    from app.models.ladder_numbers import LadderNumber
    from app.models.shelf_numbers import ShelfNumber
    from app.models.container_types import ContainerType
    from app.models.owners import Owner
    from app.models.shelf_position_numbers import ShelfPositionNumber
    from app.models.shelf_types import ShelfType
    from app.models.barcode_types import BarcodeType
    from app.models.size_class import SizeClass
    from app.models.aisles import Aisle
    from app.models.aisle_numbers import AisleNumber
    session = next(get_sqlalchemy_session())

    aisle_dict = {
        str(aisle_number): int(aisle_id)
        for aisle_id, aisle_number in session.query(
            Aisle.id, AisleNumber.number
        )
        .join(AisleNumber, AisleNumber.id == Aisle.aisle_number_id)
        .all()
    }

    side_orientations_dict = {
        str(so_name): int(so_id)
        for so_name, so_id in session.query(SideOrientation.name, SideOrientation.id).all()
    }

    ladder_number_dict = {
        int(ln_number): int(ln_id)
        for ln_number, ln_id in session.query(LadderNumber.number, LadderNumber.id).all()
    }

    shelf_number_dict = {
        int(sn_number): int(sn_id)
        for sn_number, sn_id in session.query(ShelfNumber.number, ShelfNumber.id).all()
    }

    container_type_dict = {
        str(ct_type): int(ct_id)
        for ct_type, ct_id in session.query(ContainerType.type, ContainerType.id).all()
    }

    owners_dict = {
        str(owner_name): int(owner_id)
        for owner_name, owner_id in session.query(Owner.name, Owner.id).all()
    }

    shelf_position_number_dict = {
        int(spn_number): int(spn_id)
        for spn_number, spn_id in session.query(ShelfPositionNumber.number, ShelfPositionNumber.id).all()
    }

    shelf_type_max_cap_dict = {
        int(st_id): int(max_cap)
        for st_id, max_cap in session.query(ShelfType.id, ShelfType.max_capacity).all()
    }

    barcode_types_dict = {
        str(name): [int(bct_id), str(allowed_pattern)]
        for name, bct_id, allowed_pattern in session.query(
            BarcodeType.name, BarcodeType.id, BarcodeType.allowed_pattern
        ).all()
    }

    shelf_type_lookup_query = session.query(
        ShelfType.id, SizeClass.short_name, ShelfType.type
    ).join(SizeClass, SizeClass.id == ShelfType.size_class_id).all()

    shelf_type_lookup_dict = {
        (str(short_name), str(shelf_type)): int(shelf_type_id)
        for shelf_type_id, short_name, shelf_type in shelf_type_lookup_query
    }

    session.close()

    with ThreadPoolExecutor(max_workers=24) as executor:
    # with ProcessPoolExecutor(max_workers=8) as executor:
        for chunk_start, chunk in enumerate(chunked_reader(legacy_location_path, chunk_size=5000), start=1):
            
            # DO NOT REMOVE
            # 102k rows in 5k chunks,  21 chunks
            # (1, 6), (7, 12), (13, 18), (19, 24)
            # couple this with commenting out fixtures on second run and up
            # if chunk_start < 1:
            #     continue
            # if chunk_start > 6:
            #     break

            # garbage cleanup every chunk
            gc.collect()

            futures = [
                executor.submit(
                    process_loc_row,
                    row_num, 
                    row,
                    side_orientations_dict,
                    ladder_number_dict,
                    shelf_number_dict,
                    container_type_dict,
                    owners_dict,
                    shelf_position_number_dict,
                    shelf_type_max_cap_dict,
                    barcode_types_dict,
                    shelf_type_lookup_dict,
                    aisle_dict
                )
                for row_num, row in enumerate(chunk, start=(chunk_start - 1) * 1000 + 1)
            ]

            # Collect and unpack results
            for future in futures:
                p_skipped_row_count, p_side_result, p_ladder_result, p_shelf_result, p_shelf_position_result = future.result()
                skipped_row_count += p_skipped_row_count
                if p_side_result:
                    results["sides"]["successful_rows"] += p_side_result[0]
                    results["sides"]["failed_rows"] += p_side_result[1]
                    if p_side_result[2]:
                        results["sides"]["errors"].append(p_side_result[2])
                    results["sides"]["new_record_count"] += p_side_result[3]
                if p_ladder_result:
                    results["ladders"]["successful_rows"] += p_ladder_result[0]
                    results["ladders"]["failed_rows"] += p_ladder_result[1]
                    if p_ladder_result[2]:
                        results["ladders"]["errors"].append(p_ladder_result[2])
                    results["ladders"]["new_record_count"] += p_ladder_result[3]
                if p_shelf_result:
                    results["shelves"]["successful_rows"] += p_shelf_result[0]
                    results["shelves"]["failed_rows"] += p_shelf_result[1]
                    if p_shelf_result[2]:
                        results["shelves"]["errors"].append(p_shelf_result[2])
                    results["shelves"]["new_record_count"] += p_shelf_result[3]
                if p_shelf_position_result:
                    results["shelf_positions"]["successful_rows"] += p_shelf_position_result[0]
                    results["shelf_positions"]["failed_rows"] += p_shelf_position_result[1]
                    if len(p_shelf_position_result[2]) > 0:
                        results["shelf_positions"]["errors_list"].append(p_shelf_position_result[2])
                    results["shelf_positions"]["new_record_count"] += p_shelf_position_result[3]
                    results['shelf_positions']['failed_record_count'] += p_shelf_position_result[4]


    # Gen error files
    generate_seed_error_report("loc_side_errors.csv", results["sides"]["errors"])
    generate_seed_error_report("loc_ladder_errors.csv", results["ladders"]["errors"])
    generate_seed_error_report("loc_shelf_errors.csv", results["shelves"]["errors"])
    generate_seed_error_report("loc_shelf_position_errors.csv", results["shelf_positions"]["errors_list"])

    # Summary Result
    migration_logger.info("======LOCATION INGEST COMPLETE======")
    # migration_logger.info(f"rows: {row_num}, rows skipped: {skipped_row_count}")
    migration_logger.info(f"rows skipped: {skipped_row_count}")
    # Section Results
    migration_logger.info("====SIDE RESULTS====")
    migration_logger.info(
        f"Successfully processed {results['sides']['successful_rows']} rows"
    )
    migration_logger.info(
        f"Failed to process {results['sides']['failed_rows']} rows"
    )
    migration_logger.info(f"{results['sides']['new_record_count']} new sides created")
    migration_logger.info(f"Failed data output to loc_side_errors.csv")
    migration_logger.info("====LADDER RESULTS====")
    migration_logger.info(
        f"Successfully processed {results['ladders']['successful_rows']} rows"
    )
    migration_logger.info(
        f"Failed to process {results['ladders']['failed_rows']} rows"
    )
    migration_logger.info(f"{results['ladders']['new_record_count']} new ladders created")
    migration_logger.info(f"Failed data output to loc_ladder_errors.csv")
    migration_logger.info("====Shelf RESULTS====")
    migration_logger.info(
        f"Successfully processed {results['shelves']['successful_rows']} rows"
    )
    migration_logger.info(
        f"Failed to process {results['shelves']['failed_rows']} rows"
    )
    migration_logger.info(f"{results['shelves']['new_record_count']} new shelves created")
    migration_logger.info(f"Failed data output to loc_shelf_errors.csv")
    migration_logger.info("====Shelf Position RESULTS====")
    migration_logger.info(
        f"Successfully processed {results['shelf_positions']['successful_rows']} rows"
    )
    migration_logger.info(
        f"Failed to process {results['shelf_positions']['failed_rows']} rows"
    )
    migration_logger.info(f"{results['shelf_positions']['new_record_count']} new positions created")
    migration_logger.info(f"{results['shelf_positions']['failed_record_count']} positions failed creation")
    migration_logger.info(f"Failed data output to loc_shelf_position_errors.csv")
