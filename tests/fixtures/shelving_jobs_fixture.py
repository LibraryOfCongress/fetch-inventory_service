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

SHELVING_JOBS_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get(
    "shelving_jobs"
)
CREATE_SHELVING_JOBS_SINGLE_RECORD = get_data_from_file(
    CREATE_DATA_SAMPLER_FIXTURE
).get("shelving_jobs")
UPDATED_SHELVING_JOBS_SINGLE_RECORD = get_data_from_file(
    UPDATE_DATA_SAMPLER_FIXTURE
).get("shelving_jobs")
SHELVING_JOBS_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
SHELVING_JOBS_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
SHELVING_JOBS_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
SHELVING_JOBS_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get(
    "shelving_jobs"
)
SHELVING_JOBS_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get(
    "shelving_jobs"
)


@pytest.fixture(scope="session")
def populate_shelving_job_record(client):
    """
    Fixture to populate shelving jobs records in the database.
    After the test is executed, it deletes the records created during
    the test.

    **Args:**
    - client (TestClient): The test client.
    **Yields:**
    - None
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "shelving_jobs")
