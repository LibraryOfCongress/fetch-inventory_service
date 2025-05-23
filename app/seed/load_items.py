import os, csv, re, gc

from collections import defaultdict
from concurrent.futures import as_completed, ThreadPoolExecutor
from sqlalchemy.exc import IntegrityError

from app.database.session import get_sqlalchemy_session, get_sqlalchemy_session_for_item_migration
from app.logger import migration_logger
from app.seed.scripts.load_item import load_item
from app.seed.scripts.load_non_tray import load_non_tray

from app.models.barcode_types import BarcodeType
from app.models.barcodes import Barcode
from app.models.owners import Owner
from app.models.container_types import ContainerType
from app.models.trays import Tray
from app.models.shelves import Shelf
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.shelf_positions import ShelfPosition
from app.models.size_class import SizeClass
from app.models.media_types import MediaType

current_dir = os.path.dirname(os.path.abspath(__file__))


def build_missing_non_tray_data(chunk_size=1000):
    """
    Builds a dictionary from tray.txt

    return
        {
            shelf_barcode_value: {
                "media_type": media_type_value,
                "shelved_dt": shelved_dt_value
            }
        }
    """
    legacy_tray_path = os.path.join(
        current_dir, "legacy_snapshot", "tray.txt"
    )

    missing_nt_data_dict = defaultdict(list)

    with open(legacy_tray_path, mode='r', newline='', encoding='utf-8') as csv_file:
        reader = csv.reader(csv_file)
        chunk = []
        for i, row in enumerate(reader):
            chunk.append(row)
            if (i + 1) % chunk_size == 0:
                # Process the chunk
                migration_logger.info(f"Building chunk from tray.txt to row {i + 1}")
                for row in chunk:
                    # only collect non_tray data
                    if row[0].startswith("T"):
                        # format shelf barcode value
                        shelf_barcode_value = row[4]
                        shelf_barcode_value = shelf_barcode_value.zfill(5)
                        # if len(shelf_barcode_value) < 6:
                        #     missing_zeros = 6 - len(shelf_barcode_value)
                        #     for _ in range(missing_zeros):
                        #         shelf_barcode_value = f"0{shelf_barcode_value}"

                        missing_nt_data_dict[shelf_barcode_value].append( {
                            "shelved_dt": row[9],
                            "media_type": row[2],
                            "nt_computed_barcode": row[0],
                            "size_class_short_name": row[10]
                        })

                chunk = []  # Reset the chunk

        # Process any remaining rows
        if chunk:
            migration_logger.info("Processing final chunk")
            chunk = []

    # check for incongruent matches
    for shelf_barcode in missing_nt_data_dict:
        seen = set()
        for d in missing_nt_data_dict[shelf_barcode]:
            frozen = frozenset(d.items())
            # NT's in tray.txt should only have one entry, but just in case...
            if (len(missing_nt_data_dict[shelf_barcode]) > 1) and not (frozen in seen):
                migration_logger.info(f"WARNING {len(missing_nt_data_dict[shelf_barcode])} incongruent shelved_dt & media_type matches for {shelf_barcode}")
                migration_logger.info(missing_nt_data_dict.get(shelf_barcode))
            seen.add(frozen)

    missing_nt_data_dict = dict(missing_nt_data_dict)

    return missing_nt_data_dict

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


def chunked_reader(legacy_item_path, chunk_size=1000):
    with open(
        legacy_item_path,
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


def process_item_row(
    row_num,
    row,
    # session,
    owners_dict,
    barcode_types_dict,
    container_types_dict,
    container_dict,
    shelf_position_dict,
    size_class_dict,
    media_types_dict,
    non_tray_missing_data_dict
):
    """
    Worker processor for individual rows
    Returns a collection of results for main thread.

    (
        int: skipped_row_count,
        list: item_result
    )
    """
    # session = next(get_sqlalchemy_session())
    # session = get_sqlalchemy_session_for_item_migration()
    migration_logger.info(f"PROCESSING item.txt ROW: {row_num}")
    skipped_row_count = 0

    # determine item type
    item_type = 'item'
    if bool(re.match(r"^T", row[2], flags=re.IGNORECASE)):
        item_type = 'non_tray_item'

    # field handoff
    owner_name = row[0]
    item_barcode_value = row[1]
    container_barcode_value = row[2]
    item_accession_dt = row[3]
    shelf_position_number = row[10]
    create_dt = row[8] #legacy arrival date
    status = row[16]

    if item_type == 'item':
        item_result = load_item(
            row_num,
            create_dt,
            owner_name,
            item_barcode_value,
            container_barcode_value,
            item_accession_dt,
            status,
            # session,
            owners_dict,
            barcode_types_dict,
            container_types_dict,
            container_dict
        )

        # session.close()

        return (
            skipped_row_count,
            item_result,
            None,
        )

    else:
        # skip "T0000000", is a fake NT designation
        if container_barcode_value == "T0000000":
            skipped_row_count += 1
            # session.close()
            return (
                skipped_row_count,
                None,
                None
            )

        non_tray_item_result = load_non_tray(
            row_num,
            create_dt,
            item_barcode_value,
            # media_type,
            non_tray_missing_data_dict,
            container_barcode_value,#T+shelf_barcode_value
            owner_name,
            item_accession_dt,
            # shelved_dt,
            # "NT",#size_class_short_name
            shelf_position_number,
            status,
            # session,
            container_types_dict,
            shelf_position_dict,
            size_class_dict,
            owners_dict,
            media_types_dict,
            barcode_types_dict
        )

        # session.close()

        return (
            skipped_row_count,
            None,
            non_tray_item_result
        )

def load_items():
    """
    Parallel Migration Processing on LAS Item Data

    Ingests Items from a item.txt (csv)

    Column indices are 0-based
    """
    legacy_item_path = os.path.join(
        current_dir, "legacy_snapshot", "item.txt"
    )

    # tracks pre-skip based on csv data, not skip due to processing
    skipped_row_count = 0

    results = {
        'items': {
            'successful_rows': 0,
            'failed_rows': 0,
            'errors': []
        },
        'non_tray_items': {
            'successful_rows': 0,
            'failed_rows': 0,
            'errors': []
        }
    }

    #Re-usable static dict querysets to pass through for worker execution
    session = next(get_sqlalchemy_session())
    # pending
    owners_dict = {
        o.name: o.id for o in session.query(Owner).all()
    }
    barcode_types_dict = {
        bct.name: bct.id for bct in session.query(BarcodeType).all()
    }
    container_types_dict = {
        ct.type: ct.id for ct in session.query(ContainerType).all()
    }
    tray_lookup_query = (
        session.query(
            Barcode.value.label("tray_barcode_value"),
            Tray.id.label("id"),
            Tray.media_type_id.label("media_type_id"),
            Tray.size_class_id.label("size_class_id")
        )
        .join(Tray, Tray.barcode_id == Barcode.id)
        .all()
    )
    container_dict = defaultdict(list)
    for row in tray_lookup_query:
        container_dict[row.tray_barcode_value].append(
            {"id": row.id, "media_type_id": row.media_type_id, "size_class_id": row.size_class_id}
        )
    container_dict = dict(container_dict)
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
    size_class_dict = {
        sc.short_name: sc.id for sc in session.query(SizeClass).all()
    }
    media_types_dict = {
        mt.name: mt.id for mt in session.query(MediaType).all()
    }
    non_tray_missing_data_dict = build_missing_non_tray_data()
    session.close()

    with ThreadPoolExecutor(max_workers=32) as executor:
        for chunk_start, chunk in enumerate(chunked_reader(legacy_item_path, chunk_size=100000), start=1):

            # session = get_sqlalchemy_session_for_item_migration()

            # DO NOT REMOVE (until this is handled by params)
            # 9,960,447 rows in 100k chunks
            #
            # (1, 10), (11, 21), (22, 32), (33, 43), (44, 54), (55, 65), (66, 76)
            # (77, 87), (88, 98), (99, 100)
            #
            # (1, 10), (11, 21), (22, 32), (33, 43), (44, 54) |, (55, 60), (61, 66)
            # (67, 72), (73, 78), (79, 84), (85, 90), (91, 96), (97, 100)
            #
            # 
            # each run will overwrite previous error file
            # so extract it between runs. also rebuild app between runs
            # in order to capture chunk selection changes
            # if chunk_start < 1:
            #     continue
            # if chunk_start > 10:
            #     break

            session = next(get_sqlalchemy_session())

            futures = [
                executor.submit(
                    process_item_row,
                    row_num,
                    row,
                    # session,
                    owners_dict,
                    barcode_types_dict,
                    container_types_dict,
                    container_dict,
                    shelf_position_dict,
                    size_class_dict,
                    media_types_dict,
                    non_tray_missing_data_dict
                )
                for row_num, row in enumerate(chunk, start=(chunk_start - 1) * 1000 + 1)
            ]

            item_barcode_objects = []
            standalone_item_barcode_objects = []
            item_objects = []
            standalone_item_objects = []
            nt_barcode_objects = []
            nt_objects = []
            standalone_nt_objects = []

            # Collect and unpack results
            for future in as_completed(futures):
                p_skipped_row_count, p_item_result, p_non_tray_item_result = future.result()
                skipped_row_count += p_skipped_row_count
                if p_item_result:
                    results["items"]["successful_rows"] += p_item_result[0]
                    results["items"]["failed_rows"] += p_item_result[1]
                    if p_item_result[2]:
                        results["items"]["errors"].append(p_item_result[2])
                    # p_item_result[3] are barcode objects
                    if p_item_result[3]:
                        # session.add(p_item_result[3])
                        standalone_item_barcode_objects.append(p_item_result[3])
                        item_barcode_objects.append([
                            p_item_result[3],#barcode_object
                            p_item_result[5],#row_num
                            p_item_result[6]#item_barcode_value
                        ])
                    # p_item_result[4] are item objects
                    if p_item_result[4]:
                        # session.add(p_item_result[4])
                        standalone_item_objects.append(p_item_result[4])
                        item_objects.append([
                            p_item_result[4],#item object
                            p_item_result[5],#row_num
                            p_item_result[6]#item_barcode_value
                        ])
                if p_non_tray_item_result:
                    results["non_tray_items"]["successful_rows"] += p_non_tray_item_result[0]
                    results["non_tray_items"]["failed_rows"] += p_non_tray_item_result[1]
                    if p_non_tray_item_result[2]:
                        results["non_tray_items"]["errors"].append(p_non_tray_item_result[2])
                    # p_non_tray_item_result[3] are barcode objects
                    if p_non_tray_item_result[3]:
                        # session.add(p_non_tray_item_result[3])
                        nt_barcode_objects.append(p_non_tray_item_result[3])
                    # p_non_tray_item_result[4] are non_tray_items
                    if p_non_tray_item_result[4]:
                        # session.add(p_non_tray_item_result[4])
                        standalone_nt_objects.append(p_non_tray_item_result[4])
                        nt_objects.append([
                            p_non_tray_item_result[4],#nt_object
                            p_non_tray_item_result[5],#row_num
                            p_non_tray_item_result[6]#nt_barcode_value
                        ])

            # Database ops here
            # Flush to get barcode id's before commit
            # session.flush()
            # Save all

            # session.bulk_save_objects(item_barcode_objects, return_defaults=True)
            try:
                session.bulk_save_objects(standalone_item_barcode_objects, return_defaults=True)
                session.commit()
            except Exception as e:
                # session.rollback()
                session.close()  # <-- important!
                session = next(get_sqlalchemy_session())  # open a fresh session
                # parse through for individual errors
                safe_item_barcode_objects = []
                for item_barcode_object in item_barcode_objects:
                    try:
                        session.add(item_barcode_object[0])
                        session.flush()
                        # session.commit()
                    except Exception as e:
                        session.rollback()
                        error = {
                            "row": item_barcode_object[1],
                            "item_barcode": f":: {item_barcode_object[2]}",
                            "reason": f"{e}"
                        }
                        results["items"]["errors"].append(error)
                        results["items"]["failed_rows"] += 1
                        results["items"]["successful_rows"] -= 1
                    else:
                        safe_item_barcode_objects.append(item_barcode_object[0])
                # session.add_all(safe_item_barcode_objects)
                session.bulk_save_objects(safe_item_barcode_objects, return_defaults=True)
                session.commit()

            session.bulk_save_objects(nt_barcode_objects, return_defaults=True)
            session.commit()


            # session.bulk_save_objects(item_objects, return_defaults=True)
            try:
                session.bulk_save_objects(standalone_item_objects, return_defaults=True)
                session.commit()
            except Exception as e:
                # session.rollback()
                session.close()  # <-- important!
                session = next(get_sqlalchemy_session())  # open a fresh session
                safe_item_objects = []
                for item_object in item_objects:
                    try:
                        session.add(item_object[0])
                        session.flush()
                        # session.commit()
                    except Exception as e:
                        session.rollback()
                        error = {
                            "row": item_object[1],
                            "item_barcode": f":: {item_object[2]}",
                            "reason": f"{e}"
                        }
                        results["items"]["errors"].append(error)
                        results["items"]["failed_rows"] += 1
                        results["items"]["successful_rows"] -= 1
                    else:
                        safe_item_objects.append(item_object[0])
                # session.add_all(safe_item_objects)
                session.bulk_save_objects(safe_item_objects, return_defaults=True)
                session.commit()


            # session.commit() # is this still needed - no

            # session.bulk_save_objects(nt_objects, return_defaults=True)
            try:
                session.bulk_save_objects(standalone_nt_objects, return_defaults=True)
                session.commit()
            except Exception as e:
                # session.rollback()
                session.close()  # <-- important!
                session = next(get_sqlalchemy_session())  # open a fresh session
                safe_nt_objects = []
                used_shelf_positions_ids = set()
                for non_tray_item_object in nt_objects:
                    try:
                        if non_tray_item_object[0].shelf_position_id in used_shelf_positions_ids:
                            #error skip, no rollback needed
                            error = {
                                "row": non_tray_item_object[1],
                                "non_tray_item_barcode": f":: {non_tray_item_object[2]}",
                                "reason": f"Duplicate shelf position assignment sp_id: {non_tray_item_object[0].shelf_position_id}"
                            }
                            results["non_tray_items"]["errors"].append(error)
                            results["non_tray_items"]["failed_rows"] += 1
                            results["non_tray_items"]["successful_rows"] -= 1
                            continue
                        else:
                            session.add(non_tray_item_object[0])
                            session.flush()
                        # session.commit()
                    except Exception as e:
                        session.rollback()
                        error = {
                            "row": non_tray_item_object[1],
                            "non_tray_item_barcode": f":: {non_tray_item_object[2]}",
                            "reason": f"{e}"
                        }
                        results["non_tray_items"]["errors"].append(error)
                        results["non_tray_items"]["failed_rows"] += 1
                        results["non_tray_items"]["successful_rows"] -= 1
                    else:
                        safe_nt_objects.append(non_tray_item_object[0])
                        used_shelf_positions_ids.add(non_tray_item_object[0].shelf_position_id)
                # session.add_all(safe_nt_objects)
                session.bulk_save_objects(safe_nt_objects, return_defaults=True)
                session.commit()

            # Clear resources
            session.close()
            gc.collect()

    # Gen error files
    generate_seed_error_report("item_errors.csv", results["items"]["errors"])
    generate_seed_error_report("non_tray_item_errors.csv", results["non_tray_items"]["errors"])

    # Summary Result
    migration_logger.info("======ITEM INGEST COMPLETE======")
    migration_logger.info(f"rows skipped: {skipped_row_count}")
    # Section Results
    migration_logger.info("====ITEM RESULTS====")
    migration_logger.info(
        f"Successfully processed {results['items']['successful_rows']} rows"
    )
    migration_logger.info(
        f"Failed to process {results['items']['failed_rows']} rows"
    )
    migration_logger.info(f"Failed data output to item_errors.csv")
    migration_logger.info("====NON-TRAY ITEM RESULTS====")
    migration_logger.info(
        f"Successfully processed {results['non_tray_items']['successful_rows']} rows"
    )
    migration_logger.info(
        f"Failed to process {results['non_tray_items']['failed_rows']} rows"
    )
    migration_logger.info(f"Failed data output to non_tray_item_errors.csv")
