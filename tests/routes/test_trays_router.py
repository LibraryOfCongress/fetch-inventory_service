import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.trays_fixture import (
    TRAYS_SINGLE_RECORD_RESPONSE,
    TRAYS_PAGE_DATA_RESPONSE,
    TRAYS_SIZE_DATA_RESPONSE,
    UPDATED_TRAYS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_trays_router")


def test_get_all_trays(client):
    response = client.get("/trays")
    assert response.status_code == status.HTTP_200_OK


def test_get_trays_by_page(client):
    response = client.get("/trays?page=1")
    assert response.status_code == status.HTTP_200_OK


def test_get_trays_by_page_size(client):
    response = client.get("/trays?size=10")
    assert response.status_code == status.HTTP_200_OK


def test_get_all_trays_not_found(client):
    response = client.get("/trays/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Tray ID 999 Not Found"}


def test_get_tray_by_id(client):
    response = client.get("/trays/1")
    assert response.status_code == status.HTTP_200_OK
    logging.info(f"Response: {response.json()}")
    assert response.json().get("id") == 1


def test_create_tray_record(client):
    barcodes_response = client.post(
        "/barcodes", json={"type_id": 1, "value": "5901234123601"}
    )

    assert barcodes_response.status_code == status.HTTP_201_CREATED

    response = client.post(
        "/trays",
        json={
            "accession_job_id": 1,
            "verification_job_id": 1,
            "container_type_id": 1,
            "barcode_id": barcodes_response.json().get("id"),
            "size_class_id": 1,
            "owner_id": 1,
            "media_type_id": 1,
            "shelf_position_id": 1,
            "conveyance_bin_id": 1,
            "accession_dt": "2024-01-01T00:00:00.000000",
            "shelved_dt": "2024-01-01T00:00:00.000000",
            "withdrawal_dt": "2024-01-01T00:00:00.000000",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("accession_job_id") == 1
    assert response.json().get("verification_job_id") == 1
    assert response.json().get("container_type_id") == 1
    assert response.json().get("barcode_id") == barcodes_response.json().get("id")
    assert response.json().get("size_class_id") == 1
    assert response.json().get("owner_id") == 1
    assert response.json().get("media_type_id") == 1
    assert response.json().get("shelf_position_id") == 1
    assert response.json().get("conveyance_bin_id") == 1


def test_update_tray_record(client):
    response = client.patch(f"/trays/1", json=UPDATED_TRAYS_SINGLE_RECORD)

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("accession_dt") == UPDATED_TRAYS_SINGLE_RECORD.get(
        "accession_dt"
    )
    assert response.json().get("shelved_dt") == UPDATED_TRAYS_SINGLE_RECORD.get(
        "shelved_dt"
    )
    assert response.json().get("withdrawal_dt") == UPDATED_TRAYS_SINGLE_RECORD.get(
        "withdrawal_dt"
    )


def test_update_tray_record_not_found(client):
    response = client.patch("/trays/999", json=UPDATED_TRAYS_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Tray ID 999 Not Found"


def test_delete_tray_record_success(client):
    response = client.post("/barcodes", json={"type_id": 1, "value": "5901234123461"})

    assert response.status_code == status.HTTP_201_CREATED

    response = client.post(
        "/trays/",
        json={
            "accession_job_id": 1,
            "verification_job_id": 1,
            "container_type_id": 1,
            "barcode_id": response.json().get("id"),
            "size_class_id": 1,
            "owner_id": 1,
            "media_type_id": 1,
            "shelf_position_id": 1,
            "conveyance_bin_id": 1,
            "accession_dt": "2024-01-01T00:00:00.000000",
            "shelved_dt": "2024-01-01T00:00:00.000000",
            "withdrawal_dt": "2024-01-01T00:00:00.000000",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    tray_id = response.json().get("id")

    response = client.delete(f"/trays/{tray_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == f"Tray ID {tray_id} Deleted Successfully"


def test_delete_tray_record_not_found(client):
    response = client.delete("/trays/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Tray ID 999 Not Found"
