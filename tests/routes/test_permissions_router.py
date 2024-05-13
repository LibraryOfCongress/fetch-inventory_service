import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.permissions_fixture import (
    PERMISSIONS_SINGLE_RECORD_RESPONSE,
    PERMISSIONS_PAGE_DATA_RESPONSE,
    PERMISSIONS_SIZE_DATA_RESPONSE,
    UPDATED_PERMISSIONS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_permissions_router")


def test_get_all_permissions(client):
    response = client.get("/permissions")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == PERMISSIONS_SINGLE_RECORD_RESPONSE


def test_get_permissions_by_page(client):
    response = client.get("/permissions?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == PERMISSIONS_PAGE_DATA_RESPONSE


def test_get_permissions_by_page_size(client):
    response = client.get("/permissions?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == PERMISSIONS_SIZE_DATA_RESPONSE


def test_get_all_permissions_not_found(client):
    response = client.get("/permissions/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Permission ID 999 Not Found"}


def test_get_permission_by_id(client):
    response = client.get("/permissions/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == PERMISSIONS_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_permission_record(client):
    response = client.post("/permissions/", json={"name": "test", "group_id": 2})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "test"
    assert response.json().get("group_id") == 2


def test_update_permission_record(client):
    response = client.post("/permissions/", json={"name": "test 2", "group_id": 3})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "test 2"

    permission_id = response.json().get("id")

    logging.info(f"permission_id: {permission_id}")

    response = client.patch(f"/permissions/{permission_id}", json={"name": "test 3"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == permission_id
    assert response.json().get("name") == "test 3"
    assert response.json().get("group_id") == 3


def test_update_permission_record_not_found(client):
    response = client.patch("/permissions/999", json=UPDATED_PERMISSIONS_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Permission ID 999 Not Found"


def test_delete_permission_record_success(client):
    response = client.post("/permissions/", json={"name": "test 4", "group_id": 4})
    assert response.status_code == status.HTTP_201_CREATED

    permission_id = response.json().get("id")

    response = client.delete(f"/permissions/{permission_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert (
        response.json().get("detail")
        == f"Permission ID {permission_id} Deleted Successfully"
    )


def test_delete_permission_record_not_found(client):
    response = client.delete("/permissions/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Permission ID 999 Not Found"
