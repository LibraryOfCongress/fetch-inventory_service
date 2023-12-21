from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.building_fixture import (
    BUILDING_SINGLE_RECORD_RESPONSE,
    BUILDING_PAGE_DATA_RESPONSE,
    BUILDING_SIZE_DATA_RESPONSE,
    CREATE_BUILDING_SINGLE_RECORD,
    UPDATED_BUILDING_SINGLE_RECORD
)


def test_get_all_buildings(client):
    response = client.get("/buildings")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == BUILDING_SINGLE_RECORD_RESPONSE


def test_get_all_buildings_by_page(client):
    response = client.get("/buildings?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == BUILDING_PAGE_DATA_RESPONSE


def test_get_all_buildings_by_page_size(client):
    response = client.get("/buildings?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == BUILDING_SIZE_DATA_RESPONSE


def test_get_building_by_id(client):
    response = client.get("/buildings/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == 1
    assert response.json().get("name") == CREATE_BUILDING_SINGLE_RECORD.get("name")


def test_get_buildings_by_id_not_found(client):
    response = client.get("/buildings/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_building_by_name(client):
    response = client.get(
        f'/buildings?name={CREATE_BUILDING_SINGLE_RECORD.get("name")}'
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("items")[0].get(
        "name"
    ) == CREATE_BUILDING_SINGLE_RECORD.get("name")


def test_create_building_record(client):
    response = client.post("/buildings/", json=CREATE_BUILDING_SINGLE_RECORD)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == CREATE_BUILDING_SINGLE_RECORD.get("name")


def test_update_building_record(client):
    response = client.patch("/buildings/1", json=UPDATED_BUILDING_SINGLE_RECORD)

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("name") == UPDATED_BUILDING_SINGLE_RECORD.get("name")


def test_update_building_record_not_found(client):
    response = client.patch("/buildings/999", json=UPDATED_BUILDING_SINGLE_RECORD)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_delete_building_record(client):
    data = client.post("/buildings/", json=CREATE_BUILDING_SINGLE_RECORD)

    assert data.status_code == status.HTTP_201_CREATED
    assert data.json().get("name") == CREATE_BUILDING_SINGLE_RECORD.get("name")

    response = client.delete(f"/buildings/{data.json().get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_building_record_not_found(client):
    response = client.delete("/buildings/999")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("detail") == "Not Found"
