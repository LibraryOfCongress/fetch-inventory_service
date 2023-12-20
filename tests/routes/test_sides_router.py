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
    assert response.json() == {"detail": "Not Found"}


def test_get_side_by_id(client):
    response = client.get("/sides/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == SIDES_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_side_record(client):
    response = client.post("/sides/", json={"aisle_id": 1, "side_orientation_id": 3})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("aisle_id") == 1
    assert response.json().get("side_orientation_id") == 3


def test_patch_side_record(client):
    response = client.post("/sides/orientations/", json={"name": "lefts"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "lefts"

    side_orientation_id = response.json().get("id")

    response = client.patch(
        f"/sides/2", json={"aisle_id": 1, "side_orientation_id": side_orientation_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("aisle_id") == 1
    assert response.json().get("side_orientation_id") == side_orientation_id


def test_update_side_record_not_found(client):
    response = client.patch("/sides/999", json=UPDATED_SIDES_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


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

    response = client.delete(f"/sides/{response.json().get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_side_record_not_found(client):
    response = client.delete("/sides/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
