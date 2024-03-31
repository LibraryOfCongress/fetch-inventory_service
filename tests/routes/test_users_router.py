import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.users_fixture import (
    USERS_SINGLE_RECORD_RESPONSE,
    USERS_PAGE_DATA_RESPONSE,
    USERS_SIZE_DATA_RESPONSE,
    UPDATED_USERS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_users_router")


def test_get_all_users(client):
    response = client.get("/users")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == USERS_SINGLE_RECORD_RESPONSE


def test_get_users_by_page(client):
    response = client.get("/users?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == USERS_PAGE_DATA_RESPONSE


def test_get_users_by_page_size(client):
    response = client.get("/users?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == USERS_SIZE_DATA_RESPONSE


def test_get_all_users_not_found(client):
    response = client.get("/users/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_user_by_id(client):
    response = client.get("/users/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == USERS_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_user_record(client):
    response = client.post(
        "/users/", json={
            "first_name": "Michael", "last_name":
                "Jackson"
        }
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("first_name") == "Michael"
    assert response.json().get("last_name") == "Jackson"


def test_update_user_record(client):
    response = client.post(
        "/users/", json={
            "first_name": "Bruce", "last_name":
                "Banner"
        }
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("first_name") == "Bruce"
    assert response.json().get("last_name") == "Banner"

    user_id = response.json().get("id")

    logging.info(f"user_id: {user_id}")

    response = client.patch(
        f"/users/{user_id}", json=UPDATED_USERS_SINGLE_RECORD
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("first_name") == UPDATED_USERS_SINGLE_RECORD.get(
        "first_name"
    )
    assert response.json().get("last_name") == UPDATED_USERS_SINGLE_RECORD.get(
        "last_name"
    )


def test_update_user_record_not_found(client):
    response = client.patch("/users/999", json=UPDATED_USERS_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_delete_user_record_success(client):
    response = client.post("/users/", json={"first_name": "Clark", "last_name": "Kent"})
    assert response.status_code == status.HTTP_201_CREATED

    response = client.delete(f"/users/{response.json().get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_user_record_not_found(client):
    response = client.delete("/users/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
