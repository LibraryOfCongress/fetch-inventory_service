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
        "size_class_id"
        ) == ITEMS_SINGLE_RECORD_RESPONSE.get(
        "size_class_id"
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
    assert response.json() == {"detail": "Item ID 999 Not Found"}


def test_get_item_by_id(client):
    response = client.get("/items/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == ITEMS_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


# TODO: Add test for get_item_by_id_not_found
def test_create_item_record(client):
    pass


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
    assert response.json().get("detail") == "Item ID 999 Not Found"


def test_delete_item_record_success(client):
    pass


def test_delete_item_record_not_found(client):
    response = client.delete("/items/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Item ID 999 Not Found"


def test_move_item_item_no1t_found(client):
    """
    Test when the item barcode lookup returns None.
    """
    # Simulate query for Barcode with the provided barcode_value returning None.

    response = client.post("/move/ABC123", json={"tray_barcode_value": "RS123451"})
    # Expect a validation error with the proper detail.
    assert response.status_code == 422
    assert "Item with barcode not found" in response.json()["detail"]


def test_move_item_tray_not_found(client):
    """
    Test when the tray barcode lookup returns None.
    """

    response = client.post("/move/1234567890", json={"tray_barcode_value": "TRAY001"})
    assert response.status_code == 422
    assert "Tray barcode value" in response.json()["detail"]


def test_move_item_not_verified(client):
    """
    Test when the item exists but has not been verified.
    """
    response = client.post("/move/ABC123", json={"tray_barcode_value": "TRAY001"})
    assert response.status_code == 422
    assert "has not been verified" in response.json()["detail"]


def test_move_item_success(client):
    """
    Test the successful move of an item.
    """
    # No exception should occur.
    response = client.post("/move/1234567890", json={"tray_barcode_value": "RS123451"})
    # In a successful move, the returned JSON should represent the item.
    # For this test, you may compare some fields from dummy_item.
    assert response.status_code == 200
    # For example, if the router returns the item, we expect the status to be "In"
    assert response.json().get("status") == "In"
