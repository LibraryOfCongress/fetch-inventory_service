import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.barcodes_fixture import (
    BARCODES_SINGLE_RECORD_RESPONSE,
    BARCODES_PAGE_DATA_RESPONSE,
    BARCODES_SIZE_DATA_RESPONSE,
    UPDATED_BARCODES_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_barcodes_router")


def test_get_all_barcodes(client):
    response = client.get("/barcodes")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("items")) > 0


def test_get_barcodes_by_page(client):
    response = client.get("/barcodes?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("items")) > 0


def test_get_barcodes_by_page_size(client):
    response = client.get("/barcodes?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("items")) > 0


def test_get_all_barcodes_not_found(client):
    response = client.get("/barcodes/550e8400-e29b-41d4-a716-446655440000")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_barcode_by_id(client):
    response = client.post("/barcodes", json={"type_id": 1, "value": "5901234123500"})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("type_id") == 1
    assert response.json().get("value") == "5901234123500"

    barcode_id = response.json().get("id")

    response = client.get(f"/barcodes/{barcode_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == barcode_id


def test_create_barcode_record(client):
    response = client.post("/barcodes", json={"type_id": 1, "value": "5901234123501"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("value") == "5901234123501"


def test_update_barcode_record(client):
    # Create barcode type
    response = client.post("/barcodes/types", json={"name": "test5"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "test5"

    type_id = response.json().get("id")

    response = client.post(
        "/barcodes", json={"type_id": type_id, "value": "5901234123502"}
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("type_id") == type_id
    assert response.json().get("value") == "5901234123502"

    barcode_id = response.json().get("id")

    logging.info(f"barcode_id: {barcode_id}")

    response = client.patch(f"/barcodes/{barcode_id}", json={"value": "5901234123503"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("type_id") == response.json().get("type_id")


def test_update_barcode_record_not_found(client):
    response = client.patch(
        "/barcodes/550e8400-e29b-41d4-a716-446655440000",
        json=UPDATED_BARCODES_SINGLE_RECORD,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_delete_barcode_record_success(client):
    response = client.post("/barcodes", json={"type_id": 1, "value": "5901234123504"})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("type_id") == 1
    assert response.json().get("value") == "5901234123504"

    response = client.delete(f"/barcodes/{response.json().get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_barcode_record_not_found(client):
    response = client.delete("/barcodes/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
