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

LOGGER = logging.getLogger(__name__)

AISLES_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get("aisles")
CREATE_AISLES_SINGLE_RECORD = get_data_from_file(CREATE_DATA_SAMPLER_FIXTURE).get(
    "aisles"
)
UPDATED_AISLES_SINGLE_RECORD = get_data_from_file(UPDATE_DATA_SAMPLER_FIXTURE).get(
    "aisles"
)
AISLES_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
AISLES_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
AISLES_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
AISLES_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get("aisles")
AISLES_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get("aisles")


@pytest.fixture(scope="session")
def populate_aisle_record(client):
    """
    Fixture to populate aisles records in the database.
    This fixture populates the database with records for buildings, module numbers,
    and modules. After the test is executed, it deletes the records created during
    the test.

    **Args:**
    - client (TestClient): The test client.
    **Yields:**
    - None
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "aisles")
