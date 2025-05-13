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

VERIFICATION_JOBS_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get(
    "verification_jobs"
)
CREATE_VERIFICATION_JOBS_SINGLE_RECORD = get_data_from_file(
    CREATE_DATA_SAMPLER_FIXTURE
).get("verification_jobs")
UPDATED_VERIFICATION_JOBS_SINGLE_RECORD = get_data_from_file(
    UPDATE_DATA_SAMPLER_FIXTURE
).get("verification_jobs")
VERIFICATION_JOBS_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
VERIFICATION_JOBS_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
VERIFICATION_JOBS_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
VERIFICATION_JOBS_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get(
    "verification_jobs"
)
VERIFICATION_JOBS_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get(
    "verification_jobs"
)


@pytest.fixture(scope="session")
def populate_verification_record(client):
    """
    Fixture to populate verification jobs records in the database.
    This fixture populates the database with records for buildings, module numbers,
    and modules. After the test is executed, it deletes the records created during
    the test.

    **Args:**
    - client (TestClient): The test client.
    **Yields:**
    - None
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "verification_jobs")
