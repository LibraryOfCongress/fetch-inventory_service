import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.pick_lists_fixture import (
    PICK_LISTS_SINGLE_RECORD_RESPONSE,
    PICK_LISTS_PAGE_DATA_RESPONSE,
    PICK_LISTS_SIZE_DATA_RESPONSE,
    UPDATED_PICK_LISTS_SINGLE_RECORD,
)

logger = logging.getLogger("tests.routes.test_pick_lists_router")


def test_get_all_pick_lists(client):
    response = client.get("/pick-lists")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == PICK_LISTS_SINGLE_RECORD_RESPONSE


def test_get_pick_lists_by_page(client):
    response = client.get("/pick-lists?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == PICK_LISTS_PAGE_DATA_RESPONSE


def test_get_pick_lists_by_page_size(client):
    response = client.get("/pick-lists?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == PICK_LISTS_SIZE_DATA_RESPONSE


def test_get_pick_lists_not_found(client):
    response = client.get("/pick-lists/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Pick List ID 999 Not Found"}


def test_get_pick_list_by_id(client):
    response = client.get("/pick-lists/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == PICK_LISTS_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_pick_list_record(client):
    response = client.post("/users", json={"first_name": "John", "last_name": "Wicks2"})

    assert response.status_code == status.HTTP_201_CREATED

    user_id = response.json().get("id")

    response = client.post(
        "/pick-lists", json={"user_id": user_id, "status": "Created"}
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_update_pick_list_record(client):
    response = client.post("/users", json={"first_name": "John", "last_name": "Wicks3"})

    assert response.status_code == status.HTTP_201_CREATED

    user_id = response.json().get("id")

    response = client.post(
        "/pick-lists", json={"user_id": user_id, "status": "Created"}
    )
    new_pick_list_id = response.json().get("id")

    response = client.patch(
        f"/pick-lists/{new_pick_list_id}", json={"status": "Assigned"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == new_pick_list_id
    assert response.json().get("status") == "Assigned"


def test_update_pick_list_record_not_found(client):
    response = client.patch("/pick-lists/999", json={"status": "Assigned"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Pick List ID 999 Not Found"


def test_delete_pick_list_record_success(client):
    response = client.post("/users", json={"first_name": "John", "last_name": "Wicks4"})

    assert response.status_code == status.HTTP_201_CREATED

    user_id = response.json().get("id")

    response = client.post(
        "/pick-lists", json={"user_id": user_id, "status": "Created"}
    )
    new_pick_list_id = response.json().get("id")

    response = client.delete(f"/pick-lists/{new_pick_list_id}")
    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json().get("detail")
        == f"Pick list ID {new_pick_list_id} Deleted Successfully"
    )


def test_delete_pick_list_record_not_found(client):
    response = client.delete("/pick-lists/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Pick List ID 999 Not Found"
