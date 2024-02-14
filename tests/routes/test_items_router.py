import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.items_fixture import (
    ITEMS_SINGLE_RECORD_RESPONSE,
    ITEMS_PAGE_DATA_RESPONSE,
    ITEMS_SIZE_DATA_RESPONSE,
    UPDATED_ITEMS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_items_router")


def test_get_all_items(client):
    response = client.get("/items")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("accession_dt") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "accession_dt"
    )
    assert response.json().get("accession_job_id") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "accession_job_id"
    )
    assert response.json().get("arbitrary_data") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "arbitrary_data"
    )
    assert response.json().get("condition") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "condition"
    )
    assert response.json().get("container_type_id") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "container_type_id"
    )
    assert response.json().get("media_type_id") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "media_type_id"
    )
    assert response.json().get("subcollection_id") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "subcollection_id"
    )
    assert response.json().get("title") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "title"
    )
    assert response.json().get("tray_id") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "tray_id"
    )
    assert response.json().get(
        "tray_size_class_id"
        ) == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "tray_size_class_id"
    )
    assert response.json().get(
        "verification_job_id"
        ) == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "verification_job_id"
    )
    assert response.json().get("volume") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "volume"
    )
    assert response.json().get("withdrawal_dt") == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "withdrawal_dt"
    )


def test_get_items_by_page(client):
    response = client.get("/items?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("items")) > 0


def test_get_items_by_page_size(client):
    response = client.get("/items?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("items")) > 0


def test_get_all_items_not_found(client):
    response = client.get("/items/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_item_by_id(client):
    response = client.get("/items/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == ITEMS_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_item_record(client):
    pass
    # client.post("/items", json={
    #     "accession_dt": "2023-10-08T20:46:56.764426",
    #     "accession_job_id": 1,
    #     "arbitrary_data": "Signed copy",
    #     "condition": "Good",
    #     "container_type_id": 1,
    #     "media_type_id": 1,
    #     "owner_id": 2,
    #     "subcollection_id": 1,
    #     "title": "Lord of The Rings",
    #     "tray_id": 1,
    #     "tray_size_class_id": 1,
    #     "verification_job_id": 1,
    #     "volume": "I",
    #     "withdrawal_dt": "2023-10-08T20:46:56.764426"
    # })


def test_update_item_record(client):
    response = client.patch(
        "/items/1", json={
            "volume": "II", "condition": "Poor", "arbitrary_data":
                "Unsigned copy"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("volume") == "II"
    assert response.json().get("condition") == "Poor"


def test_update_item_record_not_found(client):
    response = client.patch("/items/999", json=UPDATED_ITEMS_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_delete_item_record_success(client):
    pass


def test_delete_item_record_not_found(client):
    response = client.delete("/items/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
