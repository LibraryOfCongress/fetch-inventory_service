import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.barcode_types_fixture import (
    BARCODE_TYPES_SINGLE_RECORD_RESPONSE,
    BARCODE_TYPES_PAGE_DATA_RESPONSE,
    BARCODE_TYPES_SIZE_DATA_RESPONSE,
    UPDATED_BARCODE_TYPES_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_barcode_types_router")


def test_get_all_barcode_types(client):
    response = client.get("/barcodes/types")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == BARCODE_TYPES_SINGLE_RECORD_RESPONSE


def test_get_barcode_types_by_page(client):
    response = client.get("/barcodes/types?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == BARCODE_TYPES_PAGE_DATA_RESPONSE


def test_get_barcode_types_by_page_size(client):
    response = client.get("/barcodes/types?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == BARCODE_TYPES_SIZE_DATA_RESPONSE


def test_get_all_barcode_types_not_found(client):
    response = client.get("/barcodes/types/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_barcode_type_by_id(client):
    response = client.get("/barcodes/types/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == BARCODE_TYPES_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("id")


def test_create_barcode_type_record(client):
    response = client.post("/barcodes/types", json={"name": "test"})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "test"


def test_update_barcode_type_record(client):
    response = client.post("/barcodes/types", json={"name": "test2"})
    assert response.status_code == status.HTTP_201_CREATED

    response = client.patch(
        f"/barcodes/types/{response.json().get('id')}",
        json={"name": "test3"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("name") == "test3"


def test_update_barcode_type_record_not_found(client):
    response = client.patch(
        "/barcodes/types/999", json=UPDATED_BARCODE_TYPES_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_delete_barcode_type_record_success(client):
    response = client.post("/barcodes/types", json={"name": "test4"})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "test4"

    response = client.delete(f"/barcodes/types/{response.json().get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_barcode_type_record_not_found(client):
    response = client.delete("/barcodes/types/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
