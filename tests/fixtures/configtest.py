import os
import time
import pytest
import subprocess
import json
import logging

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy_utils import database_exists, create_database, drop_database

from app.database.session import get_session
from app.main import app

# Define the Docker command to run the Postgres container
ROOT_FILE_PATH = os.getcwd()
DOCKER_RUN_COMMAND = f"docker compose -f {ROOT_FILE_PATH}/tests/test-docker-compose.yml up -d"
DOCKER_DOWN_COMMAND = f"docker compose -f {ROOT_FILE_PATH}/tests/test-docker-compose.yml down test_db"
DOCKER_CLEANUP_COMMAND = "docker system prune -fa"

ALEMBIC_UPGRADE_COMMAND = "alembic upgrade head"
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/test_database"

# Path to your fixtures file
FIXTURES_PATH = f'{ROOT_FILE_PATH}/tests/fixtures/data_sampler.json'

# Create a new database for testing
engine = create_engine(TEST_DATABASE_URL)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def init_db():
    """
    Fixture to initialize and cleanup Docker Compose environment.

    This fixture runs the necessary commands to start and stop Docker Compose,
    and waits for the database to be ready before yielding to the test function.
    After the test function finishes, it cleans up the Docker environment.
    """
    logging.info("Starting Docker container for testing...")
    result = subprocess.run(DOCKER_RUN_COMMAND.split(), check=True, capture_output=True, text=True)

    if result.returncode != 0:
        logging.error("Failed to start Docker container: %s", result.stderr)
    else:
        logging.info("Docker container started successfully.")

    time.sleep(10)  # Wait for the database to be ready

    yield
    subprocess.run(DOCKER_DOWN_COMMAND.split())
    subprocess.run(DOCKER_CLEANUP_COMMAND.split())


@pytest.fixture(scope="session")
def test_database(init_db):
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
    yield
    drop_database(engine.url)


@pytest.fixture(scope="function")
def session():
    """
    Fixture that provides a session object for testing.
    Yields:
    - Session: The session object.
    """
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client", scope="function")
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
    with TestClient(app) as client:
        yield client

    # Clear overrides after the test is done
    app.dependency_overrides.clear()


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
    with open(fixtures_path, 'r') as file:
        data = json.load(file)
    client.post(f"/{table}", json=data.get(f"{table}"))


@pytest.fixture
def populate_building_record(client):
    """
    Fixture to populate a single building record for testing purposes.
    This fixture sends a POST request to the "/buildings/" endpoint
    with the JSON data of a sample building record. It then yields to the
    test function so that the building record can be used for testing. After
    the test function finishes, it sends a DELETE request to the
    "/buildings/1" endpoint to clean up the created record.

    Usage:
    @pytest.fixture
    def populate_building_single_record():
        # Code before the yield statement can be used to set up any necessary
        # preconditions for the test.
        yield
        # Code after the yield statement can be used to clean up any resources
        # or undo any changes made during the test.
    """
    populate_record(client, FIXTURES_PATH, "buildings")
    yield
    client.delete("/buildings/1")


@pytest.fixture
def populate_module_number_record(client):
    populate_record(client, FIXTURES_PATH, "module_numbers")
    yield
    client.delete("/module_numbers/1")


@pytest.fixture
def populate_module_record(client):
    """
    Fixture to populate module records in the database.
    This fixture populates the database with records for buildings, module numbers, and modules.
    After the test is executed, it deletes the records created during the test.
    Args:
        client (TestClient): The test client.
    Yields:
        None
    """
    populate_record(client, FIXTURES_PATH, "buildings")
    populate_record(client, FIXTURES_PATH, "module_numbers")
    populate_record(client, FIXTURES_PATH, "modules")

    yield
    client.delete("/modules/1")
    client.delete("/module_numbers/1")
    client.delete("/buildings/1")
