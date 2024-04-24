import logging
from fastapi import status

from tests.fixtures.configtest import init_db, test_database, client, session
from tests.fixtures.groups_fixture import (
    GROUPS_SINGLE_RECORD_RESPONSE,
    GROUPS_PAGE_DATA_RESPONSE,
    GROUPS_SIZE_DATA_RESPONSE,
    UPDATED_GROUPS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_groups_router")


def test_get_all_groups(client, test_database):
    response = client.get("/groups")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == GROUPS_SINGLE_RECORD_RESPONSE


def test_get_groups_by_page(client):
    response = client.get("/groups?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == GROUPS_PAGE_DATA_RESPONSE


def test_get_groups_by_page_size(client):
    response = client.get("/groups?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == GROUPS_SIZE_DATA_RESPONSE


def test_get_all_groups_not_found(client):
    response = client.get("/groups/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_group_by_id(client):
    response = client.get("/groups/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == GROUPS_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_group_record(client):
    response = client.post("/groups", json={"name": "Test Group 2"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "Test Group 2"


def test_update_group_record(client):
    response = client.post("/groups", json={"name": "Test Group 3"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "Test Group 3"

    group_id = response.json().get("id")

    logging.info(f"group_id: {group_id}")

    response = client.patch(f"/groups/{group_id}", json=UPDATED_GROUPS_SINGLE_RECORD)

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("name") == UPDATED_GROUPS_SINGLE_RECORD.get("name")


def test_update_group_record_not_found(client):
    response = client.patch("/groups/999", json=UPDATED_GROUPS_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_delete_group_record_success(client):
    response = client.post("/groups", json={"name": "Test Group 4"})
    assert response.status_code == status.HTTP_201_CREATED

    group_id = response.json().get("id")

    response = client.delete(f"/groups/{group_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == f"No Content"


def test_delete_group_record_not_found(client):
    response = client.delete("/groups/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_get_group_users_valid_id(client):
    response = client.get("/groups/1/users")
    assert response.status_code == 200


def test_get_group_users_invalid_id(client):
    response = client.get("/groups/999/users")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_add_user_to_existing_group(client):
    response = client.post("/groups/1/add_user/1")
    assert response.status_code == status.HTTP_200_OK


def test_add_user_to_non_existing_group(client):
    response = client.post("/groups/999/add_user/1")
    LOGGER.info(f"response json: {response.json()}")
    LOGGER.info(f"response status code: {response.status_code}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Group Not Found"


def test_add_non_existing_user_to_group(client):
    response = client.post("/groups/1/add_user/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "User Not Found"
