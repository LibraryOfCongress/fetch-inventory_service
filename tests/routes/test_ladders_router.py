import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.ladders_fixture import (
    LADDERS_SINGLE_RECORD_RESPONSE,
    LADDERS_PAGE_DATA_RESPONSE,
    LADDERS_SIZE_DATA_RESPONSE,
    UPDATED_LADDERS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_ladders_router")


def test_get_all_ladders(client):
    response = client.get("/ladders")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == LADDERS_SINGLE_RECORD_RESPONSE


def test_get_ladders_by_page(client):
    response = client.get("/ladders?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == LADDERS_PAGE_DATA_RESPONSE


def test_get_ladders_by_page_size(client):
    response = client.get("/ladders?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == LADDERS_SIZE_DATA_RESPONSE


def test_get_all_ladders_not_found(client):
    response = client.get("/ladders/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Ladder ID 999 Not Found"}


def test_get_ladder_by_id(client):
    response = client.get("/ladders/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == LADDERS_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_ladder_record(client):
    response = client.post("/ladders/numbers/", json={"number": 7})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 7

    ladder_number_id = response.json().get("id")

    response = client.post(
        "/ladders", json={"ladder_number_id": ladder_number_id, "side_id": 1}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("side_id") == 1
    assert response.json().get("ladder_number_id") == ladder_number_id


def test_patch_ladder_record(client):
    response = client.post("/ladders/numbers/", json={"number": 8})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 8

    ladder_number_id = response.json().get("id")

    logging.info(f"ladder_number_id: {ladder_number_id}")

    response = client.patch(
        f"/ladders/1", json={"side_id": 1, "ladder_number_id": ladder_number_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("side_id") == 1
    assert response.json().get("ladder_number_id") == ladder_number_id


def test_update_ladder_record_not_found(client):
    response = client.patch("/ladders/999", json=UPDATED_LADDERS_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Ladder ID 999 Not Found"


# TODO: Add test for delete
def test_delete_ladder_record_success(client):
    pass


def test_delete_ladder_record_not_found(client):
    response = client.delete("/ladders/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Ladder ID 999 Not Found"
