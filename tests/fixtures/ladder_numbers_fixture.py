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

LOGGER = logging.getLogger("tests.fixtures.ladder_numbers_fixture")

LADDER_NUMBERS_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get(
    "ladder_numbers"
)
CREATE_LADDER_NUMBERS_SINGLE_RECORD = get_data_from_file(
    CREATE_DATA_SAMPLER_FIXTURE
).get("ladder_numbers")
UPDATED_LADDER_NUMBERS_SINGLE_RECORD = get_data_from_file(
    UPDATE_DATA_SAMPLER_FIXTURE
).get("ladder_numbers")
LADDER_NUMBERS_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
LADDER_NUMBERS_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
LADDER_NUMBERS_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
LADDER_NUMBERS_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get(
    "ladder_numbers"
)
LADDER_NUMBERS_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get(
    "ladder_numbers"
)


@pytest.fixture(scope="session")
def populate_ladder_numbers_record(client):
    """
    Fixture to populate ladder number records in the database.
    This fixture populates the database with records for ladder numbers.
    After the test is executed, it deletes the records created during the test.

    **Args:**
    - client (TestClient): The test client.

    **Yields:**
    - None
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "ladder_numbers")
