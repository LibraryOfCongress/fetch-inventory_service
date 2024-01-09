import os
import time
import logging
import pytest
import subprocess
import json

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy_utils import database_exists, create_database, drop_database

from app.database.session import get_session
from app.main import app

# Define the Docker command to run the Postgres container
ROOT_FILE_PATH = os.getcwd()
DOCKER_RUN_COMMAND = (
    f"docker compose -f {ROOT_FILE_PATH}/tests/test-docker-compose.yml up -d"
)
DOCKER_DOWN_COMMAND = (
    f"docker compose -f {ROOT_FILE_PATH}/tests/test-docker-compose.yml down test_db"
)
DOCKER_CLEANUP_COMMAND = "docker system prune -fa"
DOCKER_CLEANUP_VOLUME_COMMAND = "docker volume prune -fa"

ALEMBIC_UPGRADE_COMMAND = "alembic upgrade head"
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/test_database"

# Path to your fixtures file
CREATE_DATA_SAMPLER_FIXTURE = (
    f"{ROOT_FILE_PATH}/tests/fixtures/payloads/create_data_sampler.json"
)
DATA_RESPONSE = f"{ROOT_FILE_PATH}/tests/fixtures/payloads/data_response.json"
UPDATE_DATA_SAMPLER_FIXTURE = (
    f"{ROOT_FILE_PATH}/tests/fixtures/payloads/update_data_sampler.json"
)
EMPTY_RESPONSE = f"{ROOT_FILE_PATH}/tests/fixtures/payloads/empty_response.json"
PAGE_EMPTY_RESPONSE = (
    f"{ROOT_FILE_PATH}/tests/fixtures/payloads/page_empty_response.json"
)
SIZE_EMPTY_RESPONSE = (
    f"{ROOT_FILE_PATH}/tests/fixtures/payloads/size_empty_response.json"
)
DATA_PAGE_RESPONSE = f"{ROOT_FILE_PATH}/tests/fixtures/payloads/data_page_response.json"
DATA_SIZE_RESPONSE = f"{ROOT_FILE_PATH}/tests/fixtures/payloads/data_size_response.json"

# Create a new database for testing
engine = create_engine(TEST_DATABASE_URL)

logger = logging.getLogger("tests.configtest")


@pytest.fixture(scope="session")
def init_db():
    """
    Fixture to initialize and cleanup Docker Compose environment.

    This fixture runs the necessary commands to start and stop Docker Compose,
    and waits for the database to be ready before yielding to the test function.
    After the test function finishes, it cleans up the Docker environment.
    """
    result = subprocess.run(
        DOCKER_RUN_COMMAND.split(), check=True, capture_output=True, text=True
    )

    if result.returncode != 0:
        logging.error("Failed to start Docker container: %s", result.stderr)
    else:
        logging.info("Docker container started successfully.")

    time.sleep(10)  # Wait for the database to be ready

    yield

    drop_database(engine.url)
    subprocess.run(DOCKER_DOWN_COMMAND.split())
    subprocess.run(DOCKER_CLEANUP_COMMAND.split())
    subprocess.run(DOCKER_CLEANUP_VOLUME_COMMAND.split())


@pytest.fixture(scope="session")
def session():
    """
    Fixture that provides a session object for testing.
    Yields:
    - Session: The session object.
    """
    session = Session(engine)
    yield session

    # Close the session after the test is done
    session.close()


@pytest.fixture(name="client", scope="session")
def client(session):
    """
    Fixture that returns a TestClient instance for testing FastAPI application.
    Parameters:
    - session: Session object for dependency injection.
    Returns:
    - TestClient: TestClient instance for testing.
    """

    # Dependency override for the session
    def get_session_override():
        return session

    # Override the dependency with the test session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client

    # Clear overrides after the test is done
    app.dependency_overrides.clear()


def get_data_from_file(file_path):
    if file_path:
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        return data
    else:
        raise ValueError("File path not provided")


def populate_record(client, fixtures_path, table):
    """
    Fixture to populate a single building record for testing purposes.
    This fixture sends a POST request to the endpoint
    with the JSON data of a sample building record. It then yields to the
    test function so that the building record can be used for testing. After
    the test function finishes, it sends a DELETE request to the
    endpoint to clean up the created record.

    Usage:
    @pytest.fixture
    def populate_record():
        # Code before the yield statement can be used to set up any necessary
        # preconditions for the test.
        yield
        # Code after the yield statement can be used to clean up any resources
        # or undo any changes made during the test.
    """
    data = get_data_from_file(fixtures_path)

    if table:
        try:
            logger.info(f"Populating table: {table}")
            logger.info(f"table: {data.get(table)}")

            if table == "module_numbers":
                return client.post("/modules/numbers", json=data.get(table))
            elif table == "aisle_numbers":
                return client.post("/aisles/numbers", json=data.get(table))
            elif table == "side_orientations":
                return client.post("/sides/orientations", json=data.get(table))
            elif table == "barcode_types":
                return client.post("/barcodes/types", json=data.get(table))
            elif table == "ladder_numbers":
                return client.post("/ladders/numbers", json=data.get(table))
            elif table == "shelf_numbers":
                return client.post("/shelves/numbers", json=data.get(table))
            elif table == "shelf_positions":
                return client.post("/shelves/positions/", json=data.get(table))
            elif table == "shelf_position_numbers":
                return client.post(f"/shelves/positions/numbers", json=data.get(table))
            elif table == "container_types":
                return client.post("/container-types", json=data.get(table))
            elif table == "owner_tiers":
                return client.post("/owners/tiers", json=data.get(table))
            elif table == "accession_jobs":
                return client.post("/accession-jobs", json=data.get(table))
            elif table == "verification_jobs":
                return client.post("/verification-jobs", json=data.get(table))
            else:
                if table == "shelves":
                    results = client.post(
                        "/barcodes", json={"type_id": 1, "value": "5901234123458"}
                    )

                    if results.status_code == 201:
                        data[table]["barcode_id"] = results.json().get("id")

                return client.post(f"/{table}", json=data.get(table))

        except Exception as e:
            raise e

    else:
        raise ValueError("Table name not provided")


@pytest.fixture(scope="session")
def test_database(client, init_db):
    """
    Initialize and test the database.

    Args :
    - init_db: A boolean indicating whether to initialize the database.

    Return:
    - None
    """
    if not database_exists(engine.url):
        create_database(engine.url)

    SQLModel.metadata.create_all(engine)

    subprocess.run(ALEMBIC_UPGRADE_COMMAND.split())

    # Populate the database with sample data
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "buildings")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "module_numbers")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "modules")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "aisle_numbers")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "aisles")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "side_orientations")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "sides")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "barcode_types")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "shelf_numbers")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "shelf_position_numbers")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "ladder_numbers")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "ladders")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "owner_tiers")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "owners")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "container_types")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "shelves")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "shelf_positions")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "accession_jobs")
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "verification_jobs")
