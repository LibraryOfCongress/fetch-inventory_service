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

SIZE_CLASS_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get("size_class")
CREATE_SIZE_CLASS_SINGLE_RECORD = get_data_from_file(CREATE_DATA_SAMPLER_FIXTURE).get(
    "size_class"
)
UPDATED_SIZE_CLASS_SINGLE_RECORD = get_data_from_file(UPDATE_DATA_SAMPLER_FIXTURE).get(
    "size_class"
)
SIZE_CLASS_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
SIZE_CLASS_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
SIZE_CLASS_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
SIZE_CLASS_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get("size_class")
SIZE_CLASS_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get("size_class")


@pytest.fixture(scope="session")
def populate_size_class_record(client):
    """
    Fixture to populate size_class records in the database.
    This fixture populates the database with records for buildings, module numbers,
    and modules. After the test is executed, it deletes the records created during
    the test.

    **Args:**
    - client (TestClient): The test client.
    **Yields:**
    - None
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "size_class")
