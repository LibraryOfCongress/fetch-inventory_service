import os, json, csv

from sqlalchemy import event
from sqlalchemyseed import load_entities_from_json, HybridSeeder
from sqlalchemy.orm import Session

from app.events import generate_location, generate_shelf_location
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.seed.seeder_session import get_session
from app.database.session import get_sqlalchemy_session
from app.logger import migration_logger
from app.seed.scripts.load_side import load_side
from app.seed.scripts.load_ladder import load_ladder
from app.seed.scripts.load_shelf import load_shelf
from app.seed.scripts.load_shelf_positions import load_shelf_positions

current_dir = os.path.dirname(os.path.abspath(__file__))


def get_seeder_session() -> Session:
    """Dependency function to get the SQLAlchemy session for seeder."""
    return get_session()


def load_seed(fixture_type, json_file):
    fixture_path = os.path.join(current_dir, "fixtures", fixture_type, json_file)
    return load_entities_from_json(fixture_path)


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


def load_storage_locations():
    """
    Determine and load unique sides, ladders,
    and shelves from loc.txt (csv)

    Column indices are 0-based
    """
    session = next(get_sqlalchemy_session())

    legacy_location_path = os.path.join(
        current_dir, "legacy_snapshot", "loc.txt"
    )

    with open(
        legacy_location_path,
        mode="r",
        newline="",
        encoding="utf-8"
    ) as file:
        reader = csv.reader(file)

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

        for row_num, row in enumerate(reader, start=1):
            # break early for testing
            # if row_num == 500:
            #     break

            migration_logger.info(f"PROCESSING loc.txt ROW: {row_num}")

            # SIDES
            side_orientation = row[1].upper()
            aisle_number = row[11]

            # business logic
            if aisle_number == "99":
                skipped_row_count += 1
                continue
            if aisle_number == "370":
                skipped_row_count += 1
                continue
            if int(aisle_number) > 499 and int(aisle_number) < 600:
                skipped_row_count += 1
                continue

            side_result = load_side(
                side_orientation,
                aisle_number,
                row_num,
                session
            )

            results["sides"]["successful_rows"] += side_result[0]
            results["sides"]["failed_rows"] += side_result[1]
            if side_result[2]:
                results["sides"]["errors"].append(side_result[2])
            results["sides"]["new_record_count"] += side_result[3]
            if not side_result[4]:
                # skip remaining processing for row
                # this keeps errors categorized and saves time
                continue

            # LADDERS
            ladder_number = row[2]
            current_side_id = side_result[4]

            # business logic
            if ladder_number == "96":
                continue
            if ladder_number == "81":
                continue

            ladder_result = load_ladder(
                ladder_number,
                current_side_id,
                row_num,
                session
            )

            results["ladders"]["successful_rows"] += ladder_result[0]
            results["ladders"]["failed_rows"] += ladder_result[1]
            if ladder_result[2]:
                results["ladders"]["errors"].append(ladder_result[2])
            results["ladders"]["new_record_count"] += ladder_result[3]
            if not ladder_result[4]:
                # skip remaining processing for row
                # this keeps errors categorized and saves time
                continue


            # SHELVES
            shelf_number = row[7]
            current_ladder_id = ladder_result[4]
            owner_name = row[4]
            shelf_height = row[9]
            shelf_width = row[13]
            shelf_depth = row[12]
            shelf_legacy_type = row[6]
            shelf_barcode_value = row[10]

            shelf_result = load_shelf(
                shelf_number,
                current_ladder_id,
                owner_name,
                shelf_height,
                shelf_width,
                shelf_depth,
                shelf_legacy_type,
                shelf_barcode_value,
                row_num,
                session
            )

            results["shelves"]["successful_rows"] += shelf_result[0]
            results["shelves"]["failed_rows"] += shelf_result[1]
            if shelf_result[2]:
                results["shelves"]["errors"].append(shelf_result[2])
            results["shelves"]["new_record_count"] += shelf_result[3]
            if not shelf_result[4]:
                # skip remaining processing for row
                # this keeps errors categorized and saves time
                continue


            # SHELF POSITIONS
            current_shelf_id = shelf_result[4]
            current_shelf_type_id = shelf_result[5]

            shelf_position_result = load_shelf_positions(
                current_shelf_id,
                current_shelf_type_id,
                row_num,
                session
            )

            results["shelf_positions"]["successful_rows"] += shelf_position_result[0]
            results["shelf_positions"]["failed_rows"] += shelf_position_result[1]
            if len(shelf_position_result[2]) > 0:
                results["shelf_positions"]["errors_list"].append(shelf_position_result[2])
            results["shelf_positions"]["new_record_count"] += shelf_position_result[3]
            results['shelf_positions']['failed_record_count'] += shelf_position_result[4]


        # Gen error files
        generate_seed_error_report("loc_side_errors.csv", results["sides"]["errors"])
        generate_seed_error_report("loc_ladder_errors.csv", results["ladders"]["errors"])
        generate_seed_error_report("loc_shelf_errors.csv", results["shelves"]["errors"])
        generate_seed_error_report("loc_shelf_position_errors.csv", results["shelf_positions"]["errors_list"])


        # Summary Result
        migration_logger.info("======LOCATION INGEST COMPLETE======")
        migration_logger.info(f"rows: {row_num}, rows skipped: {skipped_row_count}")
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

        # close db session
        session.close()


def enable_shelf_insert_listener():
    event.listen(Shelf, "after_insert", generate_shelf_location)

def enable_after_insert_listener():
    event.listen(ShelfPosition, "after_insert", generate_location)


# Tuple-List of fixtures to load
# fixture_data = [
#     ("types", "owner_tiers.json"),
#     ("entities", "tier_one_owners.json"),
#     ("entities", "tier_two_owners.json"),
#     ("entities", "buildings.json"),
#     ("entities", "modules.json"),
#     ("types", "aisle_numbers.json"),
#     ("entities", "fort_meade_aisles.json"),  # 2 modules
#     ("types", "side_orientations.json"),
#     ("entities", "sides.json"),
#     ("types", "size_classes.json"),
#     ("types", "shelf_types.json"),
#     ("types", "media_types.json"),
#     ("types", "container_types.json"),
#     ("types", "barcode_types.json"),
#     ("types", "ladder_numbers.json"),
#     ("types", "shelf_position_numbers.json"),
#     ("types", "shelf_numbers.json"),
#     ("types", "permissions.json"),
#     ("entities", "users.json"),
#     ("entities", "groups.json"),
#     ("entities", "group_permissions.json"),
#     ("entities", "user_groups.json"),
#     ("types", "request_types.json"),
#     ("types", "priorities.json"),
#     ("entities", "delivery_locations.json"),
# ]

fixture_data = [
    ("types", "client_owner_tiers.json"),#good
    ("entities", "client_owners.json"),#good
    ("entities", "client_buildings.json"),#good
    ("entities", "client_modules.json"),#good
    ("types", "client_aisle_numbers.json"),#good
    ("entities", "client_1_aisles.json"),#good
    ("entities", "client_2_aisles.json"),#good
    ("entities", "client_3_aisles.json"),#good
    ("entities", "client_4_aisles.json"),#good
    ("entities", "client_5_aisles.json"),#good
    ("entities", "client_6_aisles.json"),#good
    ("entities", "client_CSR2A_aisles.json"),#good
    ("entities", "client_CSR2B_aisles.json"),#good
    ("entities", "client_CSR2C_aisles.json"),#good
    ("entities", "client_CSR1_aisles.json"),#good
    ("entities", "client_CB_aisles.json"),#good
    ("types", "client_side_orientations.json"),#good
    ("types", "client_barcode_types.json"),#good
    ("types", "client_ladder_numbers.json"),#good
    ("types", "client_container_types.json"),#good
    ("types", "client_size_classes.json"),#WIP
    ("types", "client_shelf_types.json"),#WIP
    ("types", "client_shelf_position_numbers.json"),#WIP
    ("types", "client_media_types.json"),#WIP
    ("types", "client_permissions.json"),#WIP
    ("entities", "client_users.json"),#WIP
    ("entities", "client_groups.json"),#WIP
    ("entities", "client_group_permissions.json"),#WIP
    ("entities", "client_user_groups.json"),#WIP
    ("types", "client_request_types.json"),#WIP
    ("types", "client_priorities.json"),#WIP
    ("entities", "client_delivery_locations.json"),#WIP
    # don't client_shelf_numbers.json, too many, gen instead
]

def seed_data():
    """
    Seed static types and load migration snapshot
    """
    # below fixes logging problem here only
    migration_logger.disabled = False
    migration_logger.info("HERE WE GO!")
    session = get_seeder_session()
    seeder = HybridSeeder(session)

    for data in fixture_data:
        elements = list(data)

        migration_logger.info(f"\nSeeding {elements[1]}\n")

        seeder.seed(load_seed(elements[0], elements[1]))
        seeder.session.commit()

    load_storage_locations()
