import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.shelf_positions_fixture import (
    SHELF_POSITIONS_SINGLE_RECORD_RESPONSE,
    SHELF_POSITIONS_PAGE_DATA_RESPONSE,
    SHELF_POSITIONS_SIZE_DATA_RESPONSE,
    UPDATED_SHELF_POSITIONS_SINGLE_RECORD,
)

logging = logging.getLogger("tests.fixtures.shelf_positions_fixture")


def test_get_all_shelf_positions(client):
    response = client.get("/shelves/positions/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELF_POSITIONS_SINGLE_RECORD_RESPONSE


def test_get_shelf_positions_by_page(client):
    response = client.get("/shelves/positions/?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("page") == 1


def test_get_shelf_positions_by_page_size(client):
    response = client.get("/shelves/positions/?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("size") == 10


def test_get_all_shelf_positions_not_found(client):
    response = client.get("/shelves/positions/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_shelf_position_by_id(client):
    response = client.get("/shelves/positions/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == SHELF_POSITIONS_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("id")


def test_create_shelf_position_record(client):
    response = client.post("/shelves/positions/numbers/", json={"number": 7})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 7

    shelf_position_number_id = response.json().get("id")

    response = client.post(
        "/shelves/positions/",
        json={"shelf_id": 1, "shelf_position_number_id": shelf_position_number_id},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("shelf_id") == 1
    assert response.json().get("shelf_position_number_id") == shelf_position_number_id


def test_patch_shelf_position_record(client):
    response = client.post("/shelves/positions/numbers/", json={"number": 8})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("number") == 8

    shelf_position_number_id = response.json().get("id")

    response = client.patch(
        f"/shelves/positions/1",
        json={"shelf_id": 1, "shelf_position_number_id": shelf_position_number_id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("shelf_id") == UPDATED_SHELF_POSITIONS_SINGLE_RECORD.get(
        "shelf_id"
    )
    assert response.json().get("shelf_position_number_id") == shelf_position_number_id


def test_update_shelf_position_record_not_found(client):
    response = client.patch(
        "/shelves/positions/999", json=UPDATED_SHELF_POSITIONS_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


# TODO: Fix this testing
def test_delete_shelf_position_record_success(client):
    pass
    # Create a shelf position number
    # response = client.post("/shelves/positions/numbers/", json={"number": 9})
    # assert response.status_code == status.HTTP_201_CREATED
    # assert response.json().get("number") == 9
    #
    # shelf_position_number_id = response.json().get("id")
    #
    # # Create a barcode types
    # response = client.post("/barcodes/types", json={"name": "test6"})
    # assert response.status_code == status.HTTP_201_CREATED
    # assert response.json().get("name") == "test6"
    #
    # type_id = response.json().get("id")
    #
    # # create a new barcode
    # response = client.post(
    #     "/barcodes/", json={"type_id": type_id, "value": "5901234123505"}
    # )
    # assert response.status_code == status.HTTP_201_CREATED
    # assert response.json().get("type_id") == type_id
    # assert response.json().get("value") == "5901234123505"
    #
    # barcode_id = response.json().get("id")
    #
    # # create a new ladder number
    # response = client.post("/ladders/numbers/", json={"number": 8})
    # assert response.status_code == status.HTTP_201_CREATED
    # assert response.json().get("number") == 8
    #
    # ladder_number_id = response.json().get("id")
    #
    # # create a new ladder
    # response = client.post(
    #     "/ladders", json={"ladder_number_id": ladder_number_id, "side_id": 1}
    # )
    # assert response.status_code == status.HTTP_201_CREATED
    # assert response.json().get("side_id") == 1
    # assert response.json().get("ladder_number_id") == ladder_number_id
    #
    # ladder_id = response.json().get("id")
    #
    # # Create a shelf
    # response = client.post(
    #     "/shelves/",
    #     json={
    #         "barcode_id": barcode_id,
    #         "capacity": 33,
    #         "container_type_id": 1,
    #         "depth": 27,
    #         "height": 15.7,
    #         "ladder_id": ladder_id,
    #         "owner_id": 1,
    #         "shelf_number_id": 1,
    #         "tray_size_class_id": 1,
    #         "width": 30.33,
    #     },
    # )
    # assert response.status_code == status.HTTP_201_CREATED
    #
    # shelf_id = response.json().get("id")
    #
    # response = client.post(
    #     "/shelves/positions/",
    #     json={
    #         "shelf_id": shelf_id,
    #         "shelf_position_number_id": shelf_position_number_id,
    #     },
    # )
    # assert response.status_code == status.HTTP_201_CREATED
    #
    # response = client.delete(f"/shelves/positions/{response.json().get('id')}")
    #
    # assert response.status_code == status.HTTP_200_OK
    # assert response.json().get("status_code") == 204
    # assert response.json().get("detail") == "No Content"


def test_delete_shelf_position_record_not_found(client):
    response = client.delete("/shelves/positions/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
