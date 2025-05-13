from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.shelf_position_numbers_fixture import (
    SHELF_POSITION_NUMBER_SINGLE_RECORD_RESPONSE,
    SHELF_POSITION_NUMBER_PAGE_DATA_RESPONSE,
    SHELF_POSITION_NUMBER_SIZE_DATA_RESPONSE,
    UPDATED_SHELF_POSITION_NUMBER_SINGLE_RECORD,
)


def test_get_all_shelf_position_numbers(client):
    response = client.get("/shelves/positions/numbers/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELF_POSITION_NUMBER_SINGLE_RECORD_RESPONSE


def test_get_all_shelf_position_numbers_by_page(client):
    response = client.get("/shelves/positions/numbers?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELF_POSITION_NUMBER_PAGE_DATA_RESPONSE


def test_get_all_shelf_position_numbers_by_page_size(client):
    response = client.get("/shelves/positions/numbers?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELF_POSITION_NUMBER_SIZE_DATA_RESPONSE


def test_get_shelf_position_numbers_by_id(client):
    response = client.get("/shelves/positions/numbers/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get(
        "number"
    ) == SHELF_POSITION_NUMBER_SINGLE_RECORD_RESPONSE.get("items")[0].get("number")


def test_get_shelf_position_numbers_by_id_not_found(client):
    response = client.get("/shelves/positions/numbers/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Shelf Position Number ID 999 Not Found"}


def test_create_shelf_position_numbers_record(client):
    response = client.post("/shelves/positions/numbers", json={"number": 2})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 2


def test_update_shelf_position_numbers_record(client):
    response = client.post("/shelves/positions/numbers", json={"number": 3})
    assert response.status_code == status.HTTP_201_CREATED

    response = client.patch(
        f"/shelves/positions/numbers/{response.json().get('id')}",
        json={"number": 4},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("number") == 4


def test_update_shelf_position_numbers_record_not_found(client):
    response = client.patch("/shelves/positions/numbers/999", json={"number": 5})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Shelf Position Number ID 999 Not Found"}


def test_delete_shelf_position_numbers_record(client):
    response = client.post("/shelves/positions/numbers/", json={"number": 6})

    assert response.status_code == status.HTTP_201_CREATED

    shelf_position_number_id = response.json().get("id")

    response = client.delete(f"/shelves/positions/numbers/{shelf_position_number_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == f"Shelf Position Number ID {shelf_position_number_id} Deleted Successfully"


def test_delete_shelf_position_numbers_record_not_found(client):
    response = client.delete("/shelves/positions/numbers/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Shelf Position Number ID 999 Not Found"}
