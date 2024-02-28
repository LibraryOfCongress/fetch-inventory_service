import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.aisles_fixture import (
    AISLES_SINGLE_RECORD_RESPONSE,
    AISLES_PAGE_DATA_RESPONSE,
    AISLES_SIZE_DATA_RESPONSE,
    UPDATED_AISLES_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_aisles_router")


def test_get_all_aisles(client):
    response = client.get("/aisles")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == AISLES_SINGLE_RECORD_RESPONSE


def test_get_aisles_by_page(client):
    response = client.get("/aisles?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == AISLES_PAGE_DATA_RESPONSE


def test_get_aisles_by_page_size(client):
    response = client.get("/aisles?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == AISLES_SIZE_DATA_RESPONSE


def test_get_all_aisles_not_found(client):
    response = client.get("/aisles/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_aisle_by_id(client):
    response = client.get("/aisles/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == AISLES_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_aisle_record(client):
    response = client.post("/aisles/numbers/", json={"number": 7})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 7

    aisle_number_id = response.json().get("id")

    response = client.post(
        "/aisles", json={"building_id": 1, "aisle_number_id": aisle_number_id}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("building_id") == 1
    assert response.json().get("aisle_number_id") == aisle_number_id


def test_update_aisle_record(client):
    response = client.post("/aisles/numbers/", json={"number": 8})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 8

    aisle_number_id = response.json().get("id")

    logging.info(f"aisle_number_id: {aisle_number_id}")

    response = client.patch(
        f"/aisles/1", json={"building_id": 1, "aisle_number_id": aisle_number_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("building_id") == UPDATED_AISLES_SINGLE_RECORD.get(
        "building_id"
    )
    assert response.json().get("aisle_number_id") == aisle_number_id


def test_update_aisle_record_not_found(client):
    response = client.patch("/aisles/999", json=UPDATED_AISLES_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_delete_aisle_record_success(client):
    response = client.post("/aisles/", json={"building_id": 1, "aisle_number_id": 1})
    assert response.status_code == status.HTTP_201_CREATED

    response = client.delete(f"/aisles/{response.json().get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_aisle_record_not_found(client):
    response = client.delete("/aisles/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
