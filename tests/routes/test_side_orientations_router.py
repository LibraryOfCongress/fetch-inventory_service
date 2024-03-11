from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.side_orientations_fixture import (
    SIDE_ORIENTATIONS_SINGLE_RECORD_RESPONSE,
    SIDE_ORIENTATIONS_PAGE_DATA_RESPONSE,
    SIDE_ORIENTATIONS_SIZE_DATA_RESPONSE,
    UPDATED_SIDE_ORIENTATIONS_SINGLE_RECORD,
)


def test_get_all_side_orientations(client):
    response = client.get("/sides/orientations/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("total") > 0


def test_get_all_side_orientations_by_page(client):
    response = client.get("/sides/orientations?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("page") == 1


def test_get_all_side_orientations_by_page_size(client):
    response = client.get("/sides/orientations?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("size") == 10


def test_get_side_orientations_by_id(client):
    response = client.get("/sides/orientations/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get(
        "number"
    ) == SIDE_ORIENTATIONS_SINGLE_RECORD_RESPONSE.get("items")[0].get("number")


def test_get_side_orientations_by_id_not_found(client):
    response = client.get("/sides/orientations/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Side Orientation ID 999 Not Found"}


def test_create_side_orientations_record(client):
    response = client.post("/sides/orientations", json={"name": "right"})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("name") == "right"


# TODO: Fix this test
def test_update_side_orientations_record(client):
    pass
    # response = client.post("/sides/orientations", json={"name": "up up"})
    # assert response.status_code == status.HTTP_201_CREATED
    # assert response.json().get("name") == "up up"
    #
    # response = client.patch(
    #     f"/sides/orientations/{response.json().get('id')}",
    #     json={"name": "down down"},
    # )
    #
    # assert response.status_code == status.HTTP_200_OK
    # assert response.json().get("name") == UPDATED_SIDE_ORIENTATIONS_SINGLE_RECORD.get(
    #     "name"
    # )


def test_update_side_orientations_record_not_found(client):
    response = client.patch("/sides/orientations/999", json={"name": "left"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Side Orientation ID 999 Not Found"}


def test_delete_side_orientations_record(client):
    response = client.post("/sides/orientations/", json={"name": "upper"})

    assert response.status_code == status.HTTP_201_CREATED

    side_orientation_id = response.json().get("id")

    response = client.delete(f"/sides/orientations/{side_orientation_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == (f"Side Orientation ID "
                                             f"{side_orientation_id} Deleted Successfully")


def test_delete_side_orientations_record_not_found(client):
    response = client.delete("/sides/orientations/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Side Orientation ID 999 Not Found"}
