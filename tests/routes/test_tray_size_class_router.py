import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.size_class_fixture import (
    SIZE_CLASS_SINGLE_RECORD_RESPONSE,
    SIZE_CLASS_PAGE_DATA_RESPONSE,
    SIZE_CLASS_SIZE_DATA_RESPONSE,
    UPDATED_SIZE_CLASS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_size_class_router")


def test_get_all_size_class(client):
    response = client.get("/size_class")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SIZE_CLASS_SINGLE_RECORD_RESPONSE


def test_get_size_class_by_page(client):
    response = client.get("/size_class?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SIZE_CLASS_PAGE_DATA_RESPONSE


def test_get_size_class_by_page_size(client):
    response = client.get("/size_class?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SIZE_CLASS_SIZE_DATA_RESPONSE


def test_get_all_size_class_not_found(client):
    response = client.get("/size_class/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_size_class_by_id(client):
    response = client.get("/size_class/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == SIZE_CLASS_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("id")


def test_create_size_class_record(client):
    response = client.post("/size_class/", json={"name": "Extra Small"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "Extra Small"


def test_update_size_class_record(client):
    response = client.post("/size_class/", json={"name": "Large"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "Large"

    size_class_id = response.json().get("id")

    logging.info(f"size_class_id: {size_class_id}")

    response = client.patch(
        f"/size_class/{size_class_id}",
        json=UPDATED_SIZE_CLASS_SINGLE_RECORD,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("name") == UPDATED_SIZE_CLASS_SINGLE_RECORD.get(
        "name"
    )


def test_update_size_class_record_not_found(client):
    response = client.patch(
        "/size_class/999", json=UPDATED_SIZE_CLASS_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_delete_size_class_record_success(client):
    response = client.post("/size_class/", json={"name": "Medium"})
    assert response.status_code == status.HTTP_201_CREATED

    response = client.delete(f"/size_class/{response.json().get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_size_class_record_not_found(client):
    response = client.delete("/size_class/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
