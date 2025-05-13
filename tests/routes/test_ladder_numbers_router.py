from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.ladder_numbers_fixture import (
    LADDER_NUMBERS_SINGLE_RECORD_RESPONSE,
    LADDER_NUMBERS_PAGE_DATA_RESPONSE,
    LADDER_NUMBERS_SIZE_DATA_RESPONSE,
    UPDATED_LADDER_NUMBERS_SINGLE_RECORD,
)


def test_get_all_ladder_numbers(client):
    response = client.get("/ladders/numbers/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == LADDER_NUMBERS_SINGLE_RECORD_RESPONSE


def test_get_all_ladder_numbers_by_page(client):
    response = client.get("/ladders/numbers?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == LADDER_NUMBERS_PAGE_DATA_RESPONSE


def test_get_all_ladder_numbers_by_page_size(client):
    response = client.get("/ladders/numbers?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == LADDER_NUMBERS_SIZE_DATA_RESPONSE


def test_get_ladder_numbers_by_id(client):
    response = client.get("/ladders/numbers/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("number") == LADDER_NUMBERS_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("number")


def test_get_ladder_numbers_by_id_not_found(client):
    response = client.get("/ladders/numbers/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Ladder Number ID 999 Not Found"}


def test_create_ladder_numbers_record(client):
    response = client.post("/ladders/numbers", json={"number": 2})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 2


def test_update_ladder_numbers_record(client):
    response = client.post("/ladders/numbers", json={"number": 3})
    assert response.status_code == status.HTTP_201_CREATED

    response = client.patch(
        f"/ladders/numbers/{response.json().get('id')}",
        json=UPDATED_LADDER_NUMBERS_SINGLE_RECORD,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("number") == UPDATED_LADDER_NUMBERS_SINGLE_RECORD.get(
        "number"
    )


def test_update_ladder_numbers_record_not_found(client):
    response = client.patch("/ladders/numbers/999", json={"number": 5})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Ladder Number ID 999 Not Found"}


def test_delete_ladder_numbers_record(client):
    response = client.post("/ladders/numbers/", json={"number": 6})

    assert response.status_code == status.HTTP_201_CREATED

    ladder_number_id = response.json().get("id")

    response = client.delete(f"/ladders/numbers/{ladder_number_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == f"Ladder Number ID {ladder_number_id} Deleted Successfully"


def test_delete_ladder_numbers_record_not_found(client):
    response = client.delete("/ladders/numbers/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Ladder Number ID 999 Not Found"}
