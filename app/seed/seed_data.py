import os

from sqlalchemy import event
from sqlalchemyseed import load_entities_from_json, HybridSeeder
from sqlalchemy.orm import Session

from app.events import generate_location, generate_shelf_location
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.seed.seeder_session import get_session
from app.logger import migration_logger
from app.seed.load_storage_locations import load_storage_locations
from app.seed.load_containers import load_containers
from app.seed.load_items import load_items
from app.seed.load_available_space_calc import load_available_space_calc

current_dir = os.path.dirname(os.path.abspath(__file__))


def get_seeder_session() -> Session:
    """Dependency function to get the SQLAlchemy session for seeder."""
    return get_session()


def load_seed(fixture_type, json_file):
    fixture_path = os.path.join(current_dir, "fixtures", fixture_type, json_file)
    return load_entities_from_json(fixture_path)

def enable_shelf_insert_listener():
    event.listen(Shelf, "after_insert", generate_shelf_location)

def enable_after_insert_listener():
    event.listen(ShelfPosition, "after_insert", generate_location)


fixture_data = [
    ("types", "client_owner_tiers.json"),#good
    ("entities", "client_tier_1_owners.json"),#good
    ("entities", "client_tier_2_owners.json"),#good
    ("entities", "client_tier_3_owners.json"),#good
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
    ("types", "client_size_classes.json"),#good-ish (pending width decisions)
    ("types", "client_shelf_types.json"),#good-ish (pending NT decisions)
    ("types", "client_shelf_position_numbers.json"),#good
    ("types", "client_media_types.json"),#good
    ("types", "client_permissions.json"),#good
    ("entities", "client_users.json"),#good
    ("entities", "client_groups.json"),#good
    ("entities", "client_group_permissions.json"),#good-ish (they can set)
    ("entities", "client_user_groups.json"),#good
    ("types", "client_request_types.json"),#good
    ("types", "client_priorities.json"),#good
    ("entities", "client_delivery_locations.json"),#good
    ("types", "client_shelf_numbers.json"),#good
]

def seed_data():
    """
    Seed static types and load storage migration snapshot
    """
    # below fixes logging problem here only
    migration_logger.disabled = False
    migration_logger.info("HERE WE GO!")
    session = get_seeder_session()
    seeder = HybridSeeder(session)

    # if breaking out storage processing in chunks, comment out fixture load
    #  during subsequent runs
    for data in fixture_data:
        elements = list(data)

        migration_logger.info(f"\nSeeding {elements[1]}\n")

        seeder.seed(load_seed(elements[0], elements[1]))
        seeder.session.commit()

    # If this call ever gets moved, make sure to move location gen events
    # and turn on migration logger in new location
    load_storage_locations()


def seed_containers():
    """Load tray & non-tray migration snapshot"""
    # below fixes logging problem here only
    migration_logger.disabled = False
    migration_logger.info(
        "Yo dawg I heard you like scanning, so we put a box in your box so you can scan while you scan!"
    )
    load_containers()


def seed_items():
    """Load item migration snapshot"""
    migration_logger.disabled = False
    migration_logger.info(
        "Starting Item ingest. There will be millions..."
    )
    load_items()


def seed_initial_available_space_calc():
    """
    Loops over all shelves in the system
    to update the shelf.available_space value.
    This is separated out due to how expensive it is.
    ONLY run AFTER seed_items()
    """
    migration_logger.disabled = False
    migration_logger.info("Calculating available space for all shelves...")
    load_available_space_calc()
