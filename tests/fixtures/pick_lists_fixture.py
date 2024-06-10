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

PICK_LISTS_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get(
    "pick_lists"
)
CREATE_PICK_LISTS_SINGLE_RECORD = get_data_from_file(CREATE_DATA_SAMPLER_FIXTURE).get(
    "pick_lists"
)
UPDATED_PICK_LISTS_SINGLE_RECORD = get_data_from_file(UPDATE_DATA_SAMPLER_FIXTURE).get(
    "pick_lists"
)
PICK_LISTS_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
PICK_LISTS_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
PICK_LISTS_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
PICK_LISTS_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get(
    "pick_lists"
)
PICK_LISTS_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get(
    "pick_lists"
)


@pytest.fixture(scope="session")
def populate_aisle_record(client):
    """
    Fixture to populate pick lists records in the database.
    This fixture populates the database with records for buildings, module numbers,
    and modules. After the test is executed, it deletes the records created during
    the test.

    **Args:**
    - client (TestClient): The test client.
    **Yields:**
    - None
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "pick_lists")
