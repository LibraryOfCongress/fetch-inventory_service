import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.modules_fixture import (
    MODULES_SINGLE_RECORD_RESPONSE,
<<<<<<< HEAD
    MODULES_PAGE_DATA_RESPONSE,
    MODULES_SIZE_DATA_RESPONSE,
    UPDATED_MODULES_SINGLE_RECORD,
=======
    MODULES_EMPTY_RESPONSE,
    MODULES_PAGE_EMPTY_RESPONSE,
    MODULES_SIZE_EMPTY_RESPONSE,
    MODULES_PAGE_DATA_RESPONSE,
    MODULES_SIZE_DATA_RESPONSE,
    CREATE_MODULES_SINGLE_RECORD,
    UPDATED_MODULES_SINGLE_RECORD,
    populate_module_record,
>>>>>>> 06f29a0ec7f04d98e5623cd0113b7934b0435937
)

LOGGER = logging.getLogger("tests.routes.test_modules_router")


<<<<<<< HEAD
def test_get_all_modules(client):
=======
def test_get_empty_modules(client):
    response = client.get("/modules")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULES_EMPTY_RESPONSE


def test_get_empty_modules_by_page(client):
    response = client.get("/modules?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULES_PAGE_EMPTY_RESPONSE


def test_get_empty_modules_by_page_size(client):
    response = client.get("/modules?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULES_SIZE_EMPTY_RESPONSE


def test_get_all_modules(client, populate_module_record):
>>>>>>> 06f29a0ec7f04d98e5623cd0113b7934b0435937
    response = client.get("/modules")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULES_SINGLE_RECORD_RESPONSE


def test_get_modules_by_page(client):
    response = client.get("/modules?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULES_PAGE_DATA_RESPONSE


def test_get_modules_by_page_size(client):
    response = client.get("/modules?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == MODULES_SIZE_DATA_RESPONSE


def test_get_all_modules_not_found(client):
    response = client.get("/modules/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_module_by_id(client):
    response = client.get("/modules/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == MODULES_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


<<<<<<< HEAD
def test_create_module_record(client):
=======
def test_create_building_record(client):
>>>>>>> 06f29a0ec7f04d98e5623cd0113b7934b0435937
    response = client.post("/modules/numbers/", json={"number": 7})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 7

    module_number_id = response.json().get("id")

    response = client.post(
        "/modules", json={"building_id": 1, "module_number_id": module_number_id}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("building_id") == 1
    assert response.json().get("module_number_id") == module_number_id


def test_patch_module_record(client):
    response = client.post("/modules/numbers/", json={"number": 8})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 8

    module_number_id = response.json().get("id")

    logging.info(f"module_number_id: {module_number_id}")

    response = client.patch(
        f"/modules/1", json={"building_id": 1, "module_number_id": module_number_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("building_id") == UPDATED_MODULES_SINGLE_RECORD.get(
        "building_id"
    )
    assert response.json().get("module_number_id") == module_number_id


def test_update_module_record_not_found(client):
    response = client.patch("/modules/999", json=UPDATED_MODULES_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_delete_module_record_success(client):
    response = client.post("/modules/", json={"building_id": 1, "module_number_id": 2})
    assert response.status_code == status.HTTP_201_CREATED

    response = client.delete(f"/modules/{response.json().get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_module_record_not_found(client):
    response = client.delete("/modules/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
