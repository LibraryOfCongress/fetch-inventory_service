import pytest

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

BUILDING_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get("buildings")
CREATE_BUILDING_SINGLE_RECORD = get_data_from_file(CREATE_DATA_SAMPLER_FIXTURE).get(
    "buildings"
)
UPDATED_BUILDING_SINGLE_RECORD = get_data_from_file(UPDATE_DATA_SAMPLER_FIXTURE).get(
    "buildings"
)

BUILDING_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
BUILDING_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
BUILDING_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
BUILDING_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get("buildings")
BUILDING_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get("buildings")


@pytest.fixture(scope="session")
def populate_building_record(client):
    """
    Fixture to populate a single building record for testing purposes.
    This fixture sends a POST request to the "/buildings/" endpoint
    with the JSON data of a sample building record. It then yields to the
    test function so that the building record can be used for testing. After
    the test function finishes, it sends a DELETE request to the
    "/buildings/1" endpoint to clean up the created record.

    Usage:
    @pytest.fixture
    def populate_building_single_record():
        # Code before the yield statement can be used to set up any necessary
        # preconditions for the test.
        yield
        # Code after the yield statement can be used to clean up any resources
        # or undo any changes made during the test.
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "buildings")
