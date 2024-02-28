import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.ladders_fixture import (
    LADDERS_SINGLE_RECORD_RESPONSE,
    LADDERS_PAGE_DATA_RESPONSE,
    LADDERS_SIZE_DATA_RESPONSE,
    UPDATED_LADDERS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_ladders_router")


def test_get_all_ladders(client):
    response = client.get("/ladders")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == LADDERS_SINGLE_RECORD_RESPONSE


def test_get_ladders_by_page(client):
    response = client.get("/ladders?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == LADDERS_PAGE_DATA_RESPONSE


def test_get_ladders_by_page_size(client):
    response = client.get("/ladders?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == LADDERS_SIZE_DATA_RESPONSE


def test_get_all_ladders_not_found(client):
    response = client.get("/ladders/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_ladder_by_id(client):
    response = client.get("/ladders/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == LADDERS_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_ladder_record(client):
    response = client.post("/ladders/numbers/", json={"number": 7})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 7

    ladder_number_id = response.json().get("id")

    response = client.post(
        "/ladders", json={"ladder_number_id": ladder_number_id, "side_id": 1}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("side_id") == 1
    assert response.json().get("ladder_number_id") == ladder_number_id


def test_patch_ladder_record(client):
    response = client.post("/ladders/numbers/", json={"number": 8})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 8

    ladder_number_id = response.json().get("id")

    logging.info(f"ladder_number_id: {ladder_number_id}")

    response = client.patch(
        f"/ladders/1", json={"side_id": 1, "ladder_number_id": ladder_number_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("side_id") == 1
    assert response.json().get("ladder_number_id") == ladder_number_id


def test_update_ladder_record_not_found(client):
    response = client.patch("/ladders/999", json=UPDATED_LADDERS_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


# TODO: Add test for delete
def test_delete_ladder_record_success(client):
    pass
    # # create building
    # response = client.post("/buildings/", json={"name": "Building A"})
    #
    # assert response.status_code == status.HTTP_201_CREATED
    # assert response.json().get("name") == "Building A"
    #
    # building_id = response.json().get("id")
    #
    # # create aisle number
    # response = client.post("/aisles/numbers/", json={"number": 6})
    # assert response.status_code == status.HTTP_201_CREATED
    # assert response.json().get("number") == 6
    #
    # aisle_number_id = response.json().get("id")
    #
    # # create aisle
    # response = client.post(
    #     "/aisles/",
    #     json={"building_id": building_id, "aisle_number_id": aisle_number_id},
    # )
    # assert response.status_code == status.HTTP_201_CREATED
    #
    # # create side orientation
    # response = client.post("/sides/orientations/", json={"name": "up"})
    # assert response.status_code == status.HTTP_201_CREATED
    # assert response.json().get("name") == "up"
    #
    # side_orientation_id = response.json().get("id")
    #
    # # create a side
    # response = client.post(
    #     "/sides/",
    #     json={"aisle_id": aisle_number_id, "side_orientation_id": side_orientation_id},
    # )
    # assert response.status_code == status.HTTP_201_CREATED
    #
    # side_id = response.json().get("id")
    #
    # # create ladder number
    # response = client.post("/ladders/numbers/", json={"number": 9})
    # assert response.status_code == status.HTTP_201_CREATED
    # assert response.json().get("number") == 9
    #
    # ladder_number_id = response.json().get("id")
    #
    # response = client.post(
    #     "/ladders/", json={"side_id": side_id, "ladder_number_id": ladder_number_id}
    # )
    # assert response.status_code == status.HTTP_201_CREATED
    #
    # response = client.delete(f"/ladders/{response.json().get('id')}")
    #
    # assert response.status_code == status.HTTP_200_OK
    # assert response.json().get("status_code") == 204
    # assert response.json().get("detail") == "No Content"


def test_delete_ladder_record_not_found(client):
    response = client.delete("/ladders/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
