import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.modules_fixture import (
    MODULES_SINGLE_RECORD_RESPONSE,
    MODULES_PAGE_DATA_RESPONSE,
    MODULES_SIZE_DATA_RESPONSE,
    UPDATED_MODULES_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_modules_router")


def test_get_all_modules(client):
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
    assert response.json() == {"detail": "Module ID 999 Not Found"}


def test_get_module_by_id(client):
    response = client.get("/modules/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == MODULES_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_module_record(client):
    response = client.post("/modules", json={"building_id": 1, "module_number": "7"})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("building_id") == 1
    assert response.json().get("module_number") == "7"


def test_patch_module_record(client):
    response = client.patch(
        f"/modules/1", json={"building_id": 1, "module_number": "8"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("building_id") == UPDATED_MODULES_SINGLE_RECORD.get(
        "building_id"
    )
    assert response.json().get("module_number") == "8"


def test_update_module_record_not_found(client):
    response = client.patch("/modules/999", json=UPDATED_MODULES_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Module ID 999 Not Found"


def test_delete_module_record_success(client):
    # Create new building
    response = client.post("/buildings/", json={"name": "New Building 3"})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "New Building 3"

    building_id = response.json().get("id")

    response = client.post(
        "/modules/",
        json={"building_id": building_id, "module_number": "9"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    module_id = response.json().get("id")

    response = client.delete(f"/modules/{module_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert (
        response.json().get("detail") == f"Module ID {module_id} Deleted Successfully"
    )


def test_delete_module_record_not_found(client):
    response = client.delete("/modules/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Module ID 999 Not Found"
