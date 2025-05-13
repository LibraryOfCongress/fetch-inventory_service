import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.sides_fixture import (
    SIDES_SINGLE_RECORD_RESPONSE,
    SIDES_PAGE_DATA_RESPONSE,
    SIDES_SIZE_DATA_RESPONSE,
    UPDATED_SIDES_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_sides_router")


def test_get_all_sides(client):
    response = client.get("/sides")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SIDES_SINGLE_RECORD_RESPONSE


def test_get_sides_by_page(client):
    response = client.get("/sides?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SIDES_PAGE_DATA_RESPONSE


def test_get_sides_by_page_size(client):
    response = client.get("/sides?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SIDES_SIZE_DATA_RESPONSE


def test_get_all_sides_not_found(client):
    response = client.get("/sides/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Side ID 999 Not Found"}


def test_get_side_by_id(client):
    response = client.get("/sides/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == SIDES_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


# TODO: Add test cases for create
def test_create_side_record(client):
    pass


# TODO: Add test cases for update
def test_patch_side_record(client):
    pass


# TODO: Add test cases for update
def test_update_side_record_not_found(client):
    pass


def test_delete_side_record_success(client):
    response = client.post("/sides/orientations/", json={"name": "downs"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "downs"

    side_orientation_id = response.json().get("id")

    response = client.post(
        "/sides/", json={"aisle_id": 1, "side_orientation_id": side_orientation_id}
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("aisle_id") == 1
    assert response.json().get("side_orientation_id") == side_orientation_id

    side_id = response.json().get("id")

    response = client.delete(f"/sides/{side_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == f"Side ID {side_id} Deleted Successfully"


def test_delete_side_record_not_found(client):
    response = client.delete("/sides/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Side ID 999 Not Found"
