import pytest
import logging

from tests.fixtures.configtest import (
    CREATE_DATA_SAMPLER_FIXTURE,
    UPDATE_DATA_SAMPLER_FIXTURE,
    EMPTY_RESPONSE,
    PAGE_EMPTY_RESPONSE,
    SIZE_EMPTY_RESPONSE,
    DATA_RESPONSE,
    DATA_PAGE_RESPONSE,
    DATA_SIZE_RESPONSE,
    client,
    populate_record,
    get_data_from_file,
)

LOGGER = logging.getLogger("tests.fixtures.side_orientations_fixture")

SIDE_ORIENTATIONS_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get(
    "side_orientations"
)
CREATE_SIDE_ORIENTATIONS_SINGLE_RECORD = get_data_from_file(
    CREATE_DATA_SAMPLER_FIXTURE
).get("side_orientations")
UPDATED_SIDE_ORIENTATIONS_SINGLE_RECORD = get_data_from_file(
    UPDATE_DATA_SAMPLER_FIXTURE
).get("side_orientations")
SIDE_ORIENTATIONS_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
SIDE_ORIENTATIONS_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
SIDE_ORIENTATIONS_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
SIDE_ORIENTATIONS_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get(
    "side_orientations"
)
SIDE_ORIENTATIONS_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get(
    "side_orientations"
)


@pytest.fixture(scope="session")
def populate_side_orientations_record(client):
    """
    Fixture to populate aisle number records in the database.
    This fixture populates the database with records for aisle numbers.
    After the test is executed, it deletes the records created during the test.

    **Args:**
    - client (TestClient): The test client.

    **Yields:**
    - None
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "side_orientations")
