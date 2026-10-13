import os

# Inject required environment variables before app imports so pydantic-settings doesn't fail
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("APP_ENVIRONMENT", "test")

# Test DB URL: honor env (docker-compose / CI) and fall back to the local
# docker-compose database on port 5433 for the host-driven workflow.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/test_database"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("MIGRATION_URL", TEST_DATABASE_URL)

import time
import logging
import pytest
import subprocess
import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy_utils import database_exists, create_database, drop_database

from app.database.session import get_session
from app.database.base import Base
from app.main import app

# ... imports ...
from tests.fixtures.configtest import (
    ROOT_FILE_PATH,
    CREATE_DATA_SAMPLER_FIXTURE,
    DATA_RESPONSE,
    UPDATE_DATA_SAMPLER_FIXTURE,
    EMPTY_RESPONSE,
    PAGE_EMPTY_RESPONSE,
    SIZE_EMPTY_RESPONSE,
    DATA_PAGE_RESPONSE,
    DATA_SIZE_RESPONSE,
    get_data_from_file,
    generate_barcode_id,
    populate_record,
)

# Define the Docker command to run the Postgres container
DOCKER_RUN_COMMAND = (
    f"docker compose -f {ROOT_FILE_PATH}/tests/test-docker-compose.yml up -d"
)
DOCKER_DOWN_COMMAND = (
    f"docker compose -f {ROOT_FILE_PATH}/tests/test-docker-compose.yml down test_db"
)
DOCKER_CLEANUP_COMMAND = "docker system prune -fa"
DOCKER_CLEANUP_VOLUME_COMMAND = "docker volume prune -fa"

ALEMBIC_UPGRADE_COMMAND = "alembic upgrade head"

# When the database is provided externally (docker-compose service / CI), skip the
# self-managed docker lifecycle below and just wait for the DB to accept connections.
USE_EXTERNAL_DB = os.environ.get("TESTS_USE_EXTERNAL_DB") == "1"

# Create a new database for testing
engine = create_engine(TEST_DATABASE_URL)

logger = logging.getLogger("tests.configtest")


def _wait_for_db(timeout: int = 60):
    """Block until the Postgres server accepts connections."""
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            database_exists(engine.url)
            return
        except Exception as e:  # server not accepting connections yet
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"Test database not ready after {timeout}s: {last_err}")


@pytest.fixture(scope="session")
def init_db():
    if not USE_EXTERNAL_DB:
        result = subprocess.run(
            DOCKER_RUN_COMMAND.split(), check=True, capture_output=True, text=True
        )

        if result.returncode != 0:
            logging.error("Failed to start Docker container: %s", result.stderr)
        else:
            logging.info("Docker container started successfully.")

    _wait_for_db()

    if not database_exists(engine.url):
        create_database(engine.url)

    subprocess.run(ALEMBIC_UPGRADE_COMMAND.split(), check=True)

    yield

    if not USE_EXTERNAL_DB:
        drop_database(engine.url)
        subprocess.run(DOCKER_DOWN_COMMAND.split())
        subprocess.run(DOCKER_CLEANUP_COMMAND.split())
        subprocess.run(DOCKER_CLEANUP_VOLUME_COMMAND.split())


@pytest.fixture(scope="session")
def session(init_db):
    """
    Fixture that provides a session object for testing.

    Depends on ``init_db`` so any DB-backed test (which transitively requests this
    fixture via ``session``/``client``/``test_database``) boots and migrates the
    database, while pure unit tests that request none of them skip it entirely.
    Yields:
    - Session: The session object.
    """
    session = Session(engine, autoflush=False)
    yield session

    # Close the session after the test is done
    try:
        session.close()
    except Exception as e:
        logger.warning(f"Ignored exception during session teardown: {e}")


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
        try:
            yield session
        except Exception:
            session.rollback()
            raise

    from app.auth.dependencies import get_current_user_with_permissions
    class MockSuperUser:
        id = 999
        first_name = "GlobalMock"
        last_name = "User"
        username = "mockadmin"

        @property
        def groups(self):
            class MockPerm:
                def __init__(self, name):
                    self.name = name
            class MockGroup:
                # Provide a wide set of permissions for generic legacy tests
                permissions = [
                    MockPerm("can_access_users"), MockPerm("can_create_user"),
                    MockPerm("can_update_user"), MockPerm("can_delete_user"),
                    MockPerm("can_access_trays"), MockPerm("can_create_trays"),
                    MockPerm("can_update_trays"), MockPerm("can_delete_trays"),
                    MockPerm("manage_all_settings")
                ]
            return [MockGroup()]

    def get_user_override():
        return MockSuperUser()

    # Override the dependency with the test session and auth
    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user_with_permissions] = get_user_override

    client = TestClient(app)
    yield client

    # Clear overrides after the test is done
    app.dependency_overrides.clear()



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



    # Ensure Alembic uses the test database URL instead of the default network name
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL
    subprocess.run(ALEMBIC_UPGRADE_COMMAND.split(), env=env)
    session = Session(engine, autoflush=False)
    try:
        import app.seed.seed_fake_data

        def get_test_seeder_session():
            return Session(engine, autoflush=False)

        # Patch the seeder session generator to use our test engine
        app.seed.seed_fake_data.get_seeder_session = get_test_seeder_session

        # Patch the permissions seeder session
        import app.seed.seed_permissions_adhoc
        app.seed.seed_permissions_adhoc.get_session = get_test_seeder_session

        # Ensure all models are loaded so relationships don't throw InvalidRequestError
        from app.main import _force_load_all_models
        _force_load_all_models()

        # Seed Permissions first (idempotent, relies on explicit json load)
        app.seed.seed_permissions_adhoc.seed_new_permissions()

        # Run the official seed script
        app.seed.seed_fake_data.seed_fake_data(lightweight=True)
    finally:
        session.close()

@pytest.fixture(autouse=True, scope="session")
def _patch_session_manager():
    """
    Redirect session_manager (used by background tasks and fallback routes) to test DB.
    Without this, they try to connect to the raw 'inventory-database'.
    """
    import app.database.session as sess_mod
    original_engine = sess_mod.engine
    sess_mod.engine = engine
    yield
    sess_mod.engine = original_engine
