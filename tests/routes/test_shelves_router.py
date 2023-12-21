import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.shelves_fixture import (
    SHELVES_SINGLE_RECORD_RESPONSE,
    SHELVES_PAGE_DATA_RESPONSE,
    SHELVES_SIZE_DATA_RESPONSE,
    CREATE_SHELVES_SINGLE_RECORD,
    UPDATED_SHELVES_SINGLE_RECORD,
    create_shelf_record_data,
)

logging = logging.getLogger(__name__)


def test_get_all_shelves(client):
    response = client.get("/shelves")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELVES_SINGLE_RECORD_RESPONSE


def test_get_shelves_by_page(client):
    response = client.get("/shelves?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELVES_PAGE_DATA_RESPONSE


def test_get_shelves_by_page_size(client):
    response = client.get("/shelves?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELVES_SIZE_DATA_RESPONSE


def test_get_all_shelves_not_found(client):
    response = client.get("/shelves/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_shelf_by_id(client):
    response = client.get("/shelves/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == SHELVES_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_shelf_record(client):
    data = create_shelf_record_data(client, 10, "test1", 10)
    # create new shelf
    response = client.post("/shelves", json=data)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("capacity") == data.get("capacity")
    assert response.json().get("depth") == data.get("depth")
    assert response.json().get("height") == data.get("height")
    assert response.json().get("width") == data.get("width")


def test_patch_shelf_record(client):
    response = client.patch(
        f"/shelves/1/", json={"capacity": 35, "depth": 30, "height": 18, "width": 33}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("capacity") == 35
    assert response.json().get("depth") == 30
    assert response.json().get("height") == 18
    assert response.json().get("width") == 33


def test_update_shelf_record_not_found(client):
    response = client.patch(
        "/shelves/999/", json={"capacity": 35, "depth": 30, "height": 18, "width": 33}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_delete_shelf_record_success(client):
    data = create_shelf_record_data(client, 11, "test2", 11)
    # Create new shelf
    response = client.post("/shelves", json=data)
    assert response.status_code == status.HTTP_201_CREATED

    # Delete newly created shelf
    response = client.delete(f"/shelves/{response.json().get('id')}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_shelf_record_not_found(client):
    response = client.delete("/shelves/999/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
