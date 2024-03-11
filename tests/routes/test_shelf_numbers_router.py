import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.shelf_numbers_fixture import (
    SHELF_NUMBERS_SINGLE_RECORD_RESPONSE,
    SHELF_NUMBERS_PAGE_DATA_RESPONSE,
    SHELF_NUMBERS_SIZE_DATA_RESPONSE,
    UPDATED_SHELF_NUMBERS_SINGLE_RECORD,
)

logging = logging.getLogger(__name__)


def test_get_all_shelf_numbers(client):
    response = client.get("/shelves/numbers/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELF_NUMBERS_SINGLE_RECORD_RESPONSE


def test_get_all_shelf_numbers_by_page(client):
    response = client.get("/shelves/numbers?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELF_NUMBERS_PAGE_DATA_RESPONSE


def test_get_all_shelf_numbers_by_page_size(client):
    response = client.get("/shelves/numbers?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELF_NUMBERS_SIZE_DATA_RESPONSE


def test_get_shelf_numbers_by_id(client):
    response = client.get("/shelves/numbers/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("number") == SHELF_NUMBERS_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("number")


def test_get_shelf_numbers_by_id_not_found(client):
    response = client.get("/shelves/numbers/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Shelf Number ID 999 Not Found"}


def test_create_shelf_numbers_record(client):
    response = client.post("/shelves/numbers", json={"number": 2})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 2


def test_update_shelf_numbers_record(client):
    response = client.post("/shelves/numbers", json={"number": 3})
    assert response.status_code == status.HTTP_201_CREATED

    response = client.patch(
        f"/shelves/numbers/{response.json().get('id')}",
        json={"number": 4},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("number") == 4


def test_update_shelf_numbers_record_not_found(client):
    response = client.patch("/shelves/numbers/999", json={"number": 5})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Shelf Number ID 999 Not Found"}


def test_delete_shelf_numbers_record(client):
    response = client.post("/shelves/numbers/", json={"number": 6})

    assert response.status_code == status.HTTP_201_CREATED

    shelves_numbers_id = response.json().get("id")

    response = client.delete(f"/shelves/numbers/{shelves_numbers_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("detail") == f"Shelf Number ID {shelves_numbers_id} Deleted Successfully"


def test_delete_shelf_numbers_record_not_found(client):
    response = client.delete("/shelves/numbers/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Shelf Number ID 999 Not Found"}
