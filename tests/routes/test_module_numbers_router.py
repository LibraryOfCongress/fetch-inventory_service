from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.module_numbers_fixture import (
    MODULE_NUMBERS_SINGLE_RECORD_RESPONSE,
    MODULE_NUMBERS_EMPTY_RESPONSE,
    MODULE_NUMBERS_PAGE_EMPTY_RESPONSE,
    MODULE_NUMBERS_SIZE_EMPTY_RESPONSE,
    MODULE_NUMBERS_PAGE_DATA_RESPONSE,
    MODULE_NUMBERS_SIZE_DATA_RESPONSE,
    UPDATED_MODULE_NUMBERS_SINGLE_RECORD,
    populate_module_numbers_record,
)


def test_get_empty_module_numbers(client):
    response = client.get("/modules/numbers")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULE_NUMBERS_EMPTY_RESPONSE


def test_get_empty_module_numbers_by_page(client):
    response = client.get("/modules/numbers?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULE_NUMBERS_PAGE_EMPTY_RESPONSE


def test_get_empty_module_numbers_by_page_size(client):
    response = client.get("/modules/numbers?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULE_NUMBERS_SIZE_EMPTY_RESPONSE


def test_get_all_module_numbers(client, populate_module_numbers_record):
    response = client.get("/modules/numbers/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULE_NUMBERS_SINGLE_RECORD_RESPONSE


def test_get_all_module_numbers_by_page(client):
    response = client.get("/modules/numbers?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULE_NUMBERS_PAGE_DATA_RESPONSE


def test_get_all_module_numbers_by_page_size(client):
    response = client.get("/modules/numbers?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULE_NUMBERS_SIZE_DATA_RESPONSE


def test_get_module_numbers_by_id(client):
    response = client.get("/modules/numbers/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("number") == MODULE_NUMBERS_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("number")


def test_get_module_numbers_by_id_not_found(client):
    response = client.get("/modules/numbers/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_create_module_numbers_record(client):
    response = client.post("/modules/numbers", json={"number": 2})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 2


def test_update_module_numbers_record(client):
    response = client.post("/modules/numbers", json={"number": 3})
    assert response.status_code == status.HTTP_201_CREATED

    response = client.patch(
        f"/modules/numbers/{response.json().get('id')}",
        json=UPDATED_MODULE_NUMBERS_SINGLE_RECORD,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("number") == UPDATED_MODULE_NUMBERS_SINGLE_RECORD.get(
        "number"
    )


def test_update_module_numbers_record_not_found(client):
    response = client.patch("/modules/numbers/999", json={"number": 4})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_delete_module_numbers_record(client):
    response = client.post("/modules/numbers/", json={"number": 5})

    assert response.status_code == status.HTTP_201_CREATED

    response = client.delete(f"/modules/numbers/{response.json().get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_module_numbers_record_not_found(client):
    response = client.delete("/modules/numbers/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}
