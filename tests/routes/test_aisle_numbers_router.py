from fastapi import status

from tests.fixtures.configtest import init_db, test_database, client, session
from tests.fixtures.aisle_numbers_fixture import (
    AISLE_NUMBERS_SINGLE_RECORD_RESPONSE,
    AISLE_NUMBERS_PAGE_DATA_RESPONSE,
    AISLE_NUMBERS_SIZE_DATA_RESPONSE,
    UPDATED_AISLE_NUMBERS_SINGLE_RECORD,
)


def test_get_all_aisle_numbers(client, test_database):
    response = client.get("/aisles/numbers/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == AISLE_NUMBERS_SINGLE_RECORD_RESPONSE


def test_get_all_aisle_numbers_by_page(client):
    response = client.get("/aisles/numbers?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == AISLE_NUMBERS_PAGE_DATA_RESPONSE


def test_get_all_aisle_numbers_by_page_size(client):
    response = client.get("/aisles/numbers?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == AISLE_NUMBERS_SIZE_DATA_RESPONSE


def test_get_aisle_numbers_by_id(client):
    response = client.get("/aisles/numbers/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("number") == AISLE_NUMBERS_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("number")


def test_get_aisle_numbers_by_id_not_found(client):
    response = client.get("/aisles/numbers/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Aisle Number ID 999 Not Found"}


def test_create_aisle_numbers_record(client):
    response = client.post("/aisles/numbers", json={"number": 2})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 2


def test_update_aisle_numbers_record(client):
    response = client.post("/aisles/numbers", json={"number": 3})
    assert response.status_code == status.HTTP_201_CREATED

    response = client.patch(
        f"/aisles/numbers/{response.json().get('id')}",
        json=UPDATED_AISLE_NUMBERS_SINGLE_RECORD,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("number") == UPDATED_AISLE_NUMBERS_SINGLE_RECORD.get(
        "number"
    )


def test_update_aisle_numbers_record_not_found(client):
    response = client.patch("/aisles/numbers/999", json={"number": 4})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Aisle Number ID 999 Not Found"}


def test_delete_aisle_numbers_record(client):
    response = client.post("/aisles/numbers/", json={"number": 5})

    assert response.status_code == status.HTTP_201_CREATED

    aisle_number_id = response.json().get("id")

    response = client.delete(f"/aisles/numbers/{aisle_number_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == (f"Aisle Number ID {aisle_number_id} "
                                             f"Deleted  Successfully")


def test_delete_aisle_numbers_record_not_found(client):
    response = client.delete("/aisles/numbers/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Aisle Number ID 999 Not Found"}
