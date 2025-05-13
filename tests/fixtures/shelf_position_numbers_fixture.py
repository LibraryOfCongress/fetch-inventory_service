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

LOGGER = logging.getLogger("tests.fixtures.shelf_positions_fixture")

SHELF_POSITION_NUMBER_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get(
    "shelf_position_numbers"
)
CREATE_SHELF_POSITION_NUMBER_SINGLE_RECORD = get_data_from_file(
    CREATE_DATA_SAMPLER_FIXTURE
).get("shelf_position_numbers")
UPDATED_SHELF_POSITION_NUMBER_SINGLE_RECORD = get_data_from_file(
    UPDATE_DATA_SAMPLER_FIXTURE
).get("shelf_position_numbers")
SHELF_POSITION_NUMBER_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
SHELF_POSITION_NUMBER_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
SHELF_POSITION_NUMBER_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
SHELF_POSITION_NUMBER_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get(
    "shelf_position_numbers"
)
SHELF_POSITION_NUMBER_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get(
    "shelf_position_numbers"
)


@pytest.fixture(scope="session")
def populate_aisle_numbers_record(client):
    """
    Fixture to populate shelf position numbers records in the database.
    After the test is executed, it deletes the records created during the test.

    **Args:**
    - client (TestClient): The test client.

    **Yields:**
    - None
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "shelf_position_numbers")
