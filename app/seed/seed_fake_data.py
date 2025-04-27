import os, json, random

from sqlalchemy import event
from sqlalchemyseed import load_entities_from_json, HybridSeeder
from sqlalchemy.orm import Session

from app.events import generate_location, generate_shelf_location
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.seed.seeder_session import get_session
from app.seed.load_available_space_calc import load_available_space_calc
from app.logger import inventory_logger

current_dir = os.path.dirname(os.path.abspath(__file__))


def get_seeder_session() -> Session:
    """Dependency function to get the SQLAlchemy session for seeder."""
    return get_session()


def load_seed(fixture_type, json_file):
    fixture_path = os.path.join(current_dir, "fixtures", fixture_type, json_file)
    return load_entities_from_json(fixture_path)


def generate_ladders_for_system():
    inventory_logger.info("Generating ladders")
    ladder_session = get_seeder_session()
    ladder_seeder = HybridSeeder(ladder_session)
    # number_of_ladders = 304 # 38 ladders x 8 sides (4 aisles)
    number_of_sides = 8
    ladder_fixture_path = os.path.join(
        current_dir, "fixtures", "entities", "ladders.json"
    )
    with open(ladder_fixture_path, "r") as file:
        template_dict = json.load(file)
        for i in range(0, number_of_sides):
            ladder_dict = template_dict.copy()
            for ladder in ladder_dict["data"]:
                ladder["!side_id"]["filter"]["id"] = i + 1
            generated_file_path = os.path.join(
                current_dir, "fixtures", "entities", "gen_ladders.json"
            )
            with open(generated_file_path, "w") as file:
                json.dump(ladder_dict, file)
            # And seed

            inventory_logger.info(f"\nGenerating {i + 1} of {number_of_sides} ladders")

            ladder_seeder.seed(load_entities_from_json(generated_file_path))
            ladder_seeder.session.commit()


def generate_shelf_barcodes_for_system():
    inventory_logger.info("Generating shelf barcodes")
    barcode_session = get_seeder_session()
    barcode_seeder = HybridSeeder(barcode_session)
    barcode_fixture_path = os.path.join(
        current_dir, "fixtures", "entities", "shelf_barcodes.json"
    )
    with open(barcode_fixture_path, "r") as file:
        template_dict = json.load(file)
        # we need 2432 barcodes, template has 1
        num_barcodes = 2432  # generate 2,432 barcodes
        for i in range(0, num_barcodes):
            barcode_dict = template_dict.copy()
            for barcode in barcode_dict["data"]:
                old_value = int(barcode["value"])
                # barcode['value'] = str(old_value + 1)
                if i < 1:
                    barcode["value"] = str(old_value)
                else:
                    barcode["value"] = str(old_value + 1)
            generated_file_path = os.path.join(
                current_dir, "fixtures", "entities", "gen_shelf_barcodes.json"
            )
            with open(generated_file_path, "w") as file:
                json.dump(barcode_dict, file)
            # And seed

            inventory_logger.info(
                f"\nGenerating {i + 1} of {num_barcodes} shelf barcodes"
            )

            barcode_seeder.seed(load_entities_from_json(generated_file_path))
            barcode_seeder.session.commit()


def enable_shelf_insert_listener():
    event.listen(Shelf, "after_insert", generate_shelf_location)

def generate_shelves_for_system():
    inventory_logger.info("Generating shelves")
    shelf_session = get_seeder_session()
    shelf_seeder = HybridSeeder(shelf_session)
    shelf_fixture_path = os.path.join(
        current_dir, "fixtures", "entities", "shelves.json"
    )

    enable_shelf_insert_listener()

    with open(shelf_fixture_path, "r") as file:
        template_dict = json.load(file)
        # we need 2432 shelves, template has 1
        num_files = 2432
        for i in range(0, num_files):  # had num_files + 1
            shelf_dict = template_dict.copy()
            for shelf in shelf_dict["data"]:
                # here
                old_barcode_val = shelf["!barcode_id"]["filter"]["value"]
                # shelf['!barcode_id']['filter']['value'] = str((i + 1) + 100100) # was + 1
                if i < 1:
                    # shelf['!barcode_id']['filter']['value'] = str(int(old_barcode_val) + i + 1)
                    shelf["!barcode_id"]["filter"]["value"] = str(old_barcode_val)
                else:
                    new_barcode_value = str(int(old_barcode_val) + 1)
                    shelf["!barcode_id"]["filter"]["value"] = new_barcode_value
                cont_type = "Non-Tray"
                shelf_type_list_one = [5, 7, 9, 11, 12, 3]
                shelf_type_id = random.choice(shelf_type_list_one)
                owner_list = [
                    "Library of Congress",
                    "Consortium of Hobbits",
                    "Brethren of the Coast",
                    "Collections & Management",
                    "Congressional Research Services",
                    "Department of Buried Treasure",
                    "The Fellowship of the Ring",
                ]
                owner = random.choice(owner_list)
                if i % 3:
                    cont_type = "Tray"
                    shelf_type__list_two = [4, 6, 8, 10, 12, 14]
                    shelf_type_id = random.choice(shelf_type__list_two)
                shelf["!container_type_id"]["filter"]["type"] = cont_type
                shelf["!shelf_type_id"]["filter"]["id"] = shelf_type_id
                # get max Ok,
                shelf["!owner_id"]["filter"]["name"] = owner
                old_shelf_num = shelf["!shelf_number_id"]["filter"]["number"]
                # if old_shelf_num == 1:
                #     if i > 0: #skip first pass
                #         new_shelf_num = 2
                #     else:
                #         new_shelf_num = 1
                # else:
                #     new_shelf_num = 1

                if i == 0:
                    # shelf['!shelf_number_id']['filter']['number'] = old_shelf_num
                    new_shelf_num = old_shelf_num
                elif old_shelf_num == 8:
                    new_shelf_num = 1
                else:
                    new_shelf_num = old_shelf_num + 1
                shelf["!shelf_number_id"]["filter"]["number"] = new_shelf_num
                old_ladder_id = shelf["!ladder_id"]["filter"]["id"]
                if new_shelf_num == 1:
                    if i > 0:  # skip first pass
                        new_ladder_id = old_ladder_id + 1
                    else:
                        new_ladder_id = old_ladder_id
                else:
                    new_ladder_id = old_ladder_id
                shelf["!ladder_id"]["filter"]["id"] = new_ladder_id
            generated_file_path = os.path.join(
                current_dir, "fixtures", "entities", "gen_shelves.json"
            )
            with open(generated_file_path, "w") as file:
                json.dump(shelf_dict, file)
            # And seed

            inventory_logger.info(f"\nGenerating {i + 1} of {num_files} shelves")
            shelf_seeder.seed(load_entities_from_json(generated_file_path))
            shelf_seeder.session.commit()


def enable_after_insert_listener():
    event.listen(ShelfPosition, "after_insert", generate_location)


def generate_shelf_positions_for_system():
    inventory_logger.info("Generating shelf positions")
    shelf_pos_session = get_seeder_session()
    shelf_pos_seeder = HybridSeeder(shelf_pos_session)
    shelf_pos_fixture_path = os.path.join(
        current_dir, "fixtures", "entities", "shelf_positions.json"
    )

    enable_after_insert_listener()

    with open(shelf_pos_fixture_path, "r") as file:
        template_dict = json.load(file)
        # we need 3 positions per shelf, template has 3
        # 8 pos * 2432
        num_shelves = 2432
        for i in range(0, num_shelves):
            shelf_pos_dict = template_dict.copy()
            for shelf_position in shelf_pos_dict["data"]:
                old_shelf_id = shelf_position["!shelf_id"]["filter"]["id"]
                if i > 0:
                    shelf_position["!shelf_id"]["filter"]["id"] = 1 + old_shelf_id
            generated_file_path = os.path.join(
                current_dir, "fixtures", "entities", "gen_shelf_positions.json"
            )
            with open(generated_file_path, "w") as file:
                json.dump(shelf_pos_dict, file)
            # And seed

            inventory_logger.info(
                f"\nGenerating {i + 1} of {num_shelves} shelf positions"
            )
            shelf_pos_seeder.seed(load_entities_from_json(generated_file_path))
            shelf_pos_seeder.session.commit()


# Tuple-List of fixtures to load
fake_data = [
    ("types", "owner_tiers.json"),
    ("entities", "tier_one_owners.json"),
    ("entities", "tier_two_owners.json"),
    ("entities", "buildings.json"),
    ("entities", "modules.json"),
    ("types", "aisle_numbers.json"),
    ("entities", "fort_meade_aisles.json"),  # 2 modules
    ("types", "side_orientations.json"),
    ("entities", "sides.json"),
    ("types", "size_classes.json"),
    ("types", "shelf_types.json"),
    ("types", "media_types.json"),
    ("types", "container_types.json"),
    ("types", "barcode_types.json"),
    ("types", "ladder_numbers.json"),
    ("types", "shelf_position_numbers.json"),
    ("types", "shelf_numbers.json"),
    ("types", "permissions.json"),
    ("entities", "users.json"),
    ("entities", "groups.json"),
    ("entities", "group_permissions.json"),
    ("entities", "user_groups.json"),
    ("types", "request_types.json"),
    ("types", "priorities.json"),
    ("entities", "delivery_locations.json"),
]


def seed_fake_data():
    inventory_logger.disabled = False
    inventory_logger.info("Staring process to seed fake data...")
    session = get_seeder_session()
    seeder = HybridSeeder(session)

    for data in fake_data:
        elements = list(data)

        inventory_logger.info(f"\nSeeding element: {elements[0]} from {elements[1]}\n")

        seeder.seed(load_seed(elements[0], elements[1]))
        seeder.session.commit()
    """
    Ladders would need either 8 files,
    so instead we'll script to generate ladders 1-38
    across 8 sides (4 aisles)
    """
    # 304 ladders
    generate_ladders_for_system()
    # 2432 shelf barcodes
    generate_shelf_barcodes_for_system()
    # 2432 shelves (8 shelves per ladder)
    generate_shelves_for_system()
    # 41040 shelf positions (3 positions per shelf) to match capacity=3
    generate_shelf_positions_for_system()
    # set available space on shelves
    load_available_space_calc()
