import pytest
import logging
import random
import json

from fastapi import status

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

SHELVES_SINGLE_RECORD_RESPONSE = get_data_from_file(DATA_RESPONSE).get("shelves")
CREATE_SHELVES_SINGLE_RECORD = get_data_from_file(CREATE_DATA_SAMPLER_FIXTURE).get(
    "shelves"
)
UPDATED_SHELVES_SINGLE_RECORD = get_data_from_file(UPDATE_DATA_SAMPLER_FIXTURE).get(
    "shelves"
)
SHELVES_EMPTY_RESPONSE = get_data_from_file(EMPTY_RESPONSE)
SHELVES_PAGE_EMPTY_RESPONSE = get_data_from_file(PAGE_EMPTY_RESPONSE)
SHELVES_SIZE_EMPTY_RESPONSE = get_data_from_file(SIZE_EMPTY_RESPONSE)
SHELVES_PAGE_DATA_RESPONSE = get_data_from_file(DATA_PAGE_RESPONSE).get("shelves")
SHELVES_SIZE_DATA_RESPONSE = get_data_from_file(DATA_SIZE_RESPONSE).get("shelves")


@pytest.fixture(scope="session")
def populate_aisle_record(client):
    """
    Fixture to populate shelves records in the database.
    After the test is executed, it deletes the records created during
    the test.

    **Args:**
    - client (TestClient): The test client.

    **Yields:**
    - None
    """
    populate_record(client, CREATE_DATA_SAMPLER_FIXTURE, "shelves")


def create_shelf_record_data(client, ladder_number_id, owner_name, shelf_number_id):
    barcode_valuer = random.randrange(1000000000, 9999999999999)

    # copy shelf data
    data = CREATE_SHELVES_SINGLE_RECORD

    # create new barcode
    response = client.post(
        "/barcodes/", json={"type_id": 1, "value": str(barcode_valuer)}
    )

    # add barcode id to data
    data["barcode_id"] = response.json().get("id")

    # add container type id to data
    data["container_type_id"] = 1

    # create new ladder number
    response = client.post("/ladders/numbers/", json={"number": ladder_number_id})

    # create new ladder
    response = client.post(
        "/ladders/", json={"ladder_number_id": response.json().get("id"), "side_id": 1}
    )
    data["ladder_id"] = response.json().get("id")

    # create new owner
    response = client.post("/owners/", json={"name": owner_name, "owner_tier_id": 1})

    # add owner id to data
    data["owner_id"] = response.json().get("id")

    # create shelf number
    response = client.post("/shelves/numbers/", json={"number": shelf_number_id})
    data["shelf_number_id"] = response.json().get("id")

    return data
