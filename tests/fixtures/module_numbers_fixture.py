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

LOGGER = logging.getLogger("tests.fixtures.module_numbers_fixture")

MODULE_NUMBERS_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get(
    "modules_numbers"
)
CREATE_MODULE_NUMBERS_SINGLE_RECORD = get_data_from_file(
    CREATE_DATA_SAMPLER_FIXTURE
).get("modules_numbers")
UPDATED_MODULE_NUMBERS_SINGLE_RECORD = get_data_from_file(
    UPDATE_DATA_SAMPLER_FIXTURE
).get("modules_numbers")
MODULE_NUMBERS_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
MODULE_NUMBERS_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
MODULE_NUMBERS_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
MODULE_NUMBERS_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get(
    "modules_numbers"
)
MODULE_NUMBERS_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get(
    "modules_numbers"
)


@pytest.fixture(scope="session")
def populate_module_numbers_record(client):
    """
    Fixture to populate module number records in the database.
    This fixture populates the database with records for module numbers.
    After the test is executed, it deletes the records created during the test.

    **Args:**
    - client (TestClient): The test client.

    **Yields:**
    - None
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "modules_numbers")
