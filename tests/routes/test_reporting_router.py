import pytest
from fastapi import status

from app.filter_params import NonTrayItemsCountParams
from tests.fixtures.configtest import init_db, test_database, client, session


def test_get_accessioned_items_aggregate_no_filters(client, test_database):
    # Call the function
    response = client.get("/reporting/accession-items", params={})

    # Assert the response
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_get_accessioned_items_aggregate_with_owner_id(client):
    # Call the function
    response = client.get("/reporting/accession-items", params={"owner_id": [1]})

    # Assert the response
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_accessioned_items_aggregate_with_size_class_id(client):
    # Call the function
    response = client.get("/reporting/accession-items", params={"size_class_id": [1]})

    # Assert the response
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_accessioned_items_aggregate_with_media_type_id(client):
    # Call the function
    response = client.get("/reporting/accession-items", params={"media_type_id": [1]})

    # Assert the response
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_accessioned_items_aggregate_with_from_dt(client):
    # Call the function
    response = client.get("/reporting/accession-items", params={"from_dt": "2023-10-08T20:46:56.764426"})

    # Assert the response
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_accessioned_items_aggregate_with_to_dt(client):
    # Call the function
    response = client.get("/reporting/accession-items", params={"to_dt": "2023-10-08T20:46:56.764426"})

    # Assert the response
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_accessioned_items_aggregate_with_all_filters(client):
    owner_id = 1
    size_class_id = 1
    media_type_id = 1

    owner = client.get(f"/owners/{owner_id}")
    assert owner.status_code == status.HTTP_200_OK
    assert owner.json().get("id") == 1

    owner_name = owner.json().get("name")

    size_class = client.get(f"/size_class/{size_class_id}")
    assert size_class.status_code == status.HTTP_200_OK
    assert size_class.json().get("id") == 1

    size_class_name = size_class.json().get("name")

    media_type = client.get(f"/media_types/{media_type_id}")
    assert media_type.status_code == status.HTTP_200_OK
    assert media_type.json().get("id") == 1

    media_type_name = media_type.json().get("name")

    # Call the function
    response = client.get("/reporting/accession-items", params={
        "owner_id": [owner_id],
        "size_class_id": [size_class_id],
        "media_type_id": [media_type_id],
        "from_dt": "2023-10-08T20:46:56.764426",
        "to_dt": "2023-10-08T20:46:56.764426"
    })

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["count"] == 1
    assert response.json()["items"][0].get("owner_name") == owner_name
    assert response.json()["items"][0].get("size_class_name") == size_class_name
    assert response.json()["items"][0].get("media_type_name") == media_type_name


def test_get_aisle_items_count_valid_building(client):
    response = client.get("/aisles/items_count?building_id=1&aisle_num_from=1&aisle_num_to=10")
    assert response.status_code == 200


def test_get_aisle_items_count_invalid_building(client):
    response = client.get("/aisles/items_count?building_id=999&aisle_num_from=1&aisle_num_to=10")
    assert response.status_code == 404
    assert response.json()["detail"] == "Building not found"


def test_get_aisle_items_count_missing_building_id(client):
    response = client.get("/aisles/items_count?aisle_num_from=1&aisle_num_to=10")
    assert response.status_code == 422
    assert "building_id" in response.json()["detail"][0]["loc"]


def test_get_aisle_items_count_missing_aisle_num_from(client):
    response = client.get("/aisles/items_count?building_id=1&aisle_num_to=10")
    assert response.status_code == 422
    assert "aisle_num_from" in response.json()["detail"][0]["loc"]


def test_get_aisle_items_count_missing_aisle_num_to(client):
    response = client.get("/aisles/items_count?building_id=1&aisle_num_from=1")
    assert response.status_code == 422
    assert "aisle_num_to" in response.json()["detail"][0]["loc"]


def test_get_aisle_items_count_invalid_aisle_num_from(client):
    response = client.get("/aisles/items_count?building_id=1&aisle_num_from=abc&aisle_num_to=10")
    assert response.status_code == 422
    assert "aisle_num_from" in response.json()["detail"][0]["loc"]


def test_get_aisle_items_count_invalid_aisle_num_to(client):
    response = client.get("/aisles/items_count?building_id=1&aisle_num_from=1&aisle_num_to=abc")
    assert response.status_code == 422
    assert "aisle_num_to" in response.json()["detail"][0]["loc"]


def test_get_aisle_items_count_aisle_num_from_greater_than_aisle_num_to(client):
    response = client.get("/aisles/items_count?building_id=1&aisle_num_from=10&aisle_num_to=1")
    assert response.status_code == 200


def test_get_aisles_items_count_csv(client):
    # Test with valid building ID and aisle numbers
    params = {
        "building_id": 1,
        "aisle_num_from": 1,
        "aisle_num_to": 10
    }
    response = client.get("/aisles/items_count/download", params=params)
    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == "attachment; filename=aisles_item_count.csv"
    assert response.headers["Content-Type"] == "text/csv"

    # Test with invalid building ID
    params = {
        "building_id": 999,
        "aisle_num_from": 1,
        "aisle_num_to": 10
    }
    response = client.get("/aisles/items_count/download", params=params)
    assert response.status_code == 404
    assert response.json()["detail"] == "Building not found"

    # Test with missing building ID
    params = {
        "aisle_num_from": 1,
        "aisle_num_to": 10
    }
    response = client.get("/aisles/items_count/download", params=params)
    assert response.status_code == 422
    assert "building_id" in response.json()["detail"][0]["loc"]

    # Test with missing aisle numbers
    params = {
        "building_id": 1
    }
    response = client.get("/aisles/items_count/download", params=params)
    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == "attachment; filename=aisles_item_count.csv"
    assert response.headers["Content-Type"] == "text/csv"

    # Test with invalid aisle numbers
    params = {
        "building_id": 1,
        "aisle_num_from": "abc",
        "aisle_num_to": 10
    }
    response = client.get("/aisles/items_count/download", params=params)
    assert response.status_code == 422
    assert "aisle_num_from" in response.json()["detail"][0]["loc"]


def test_get_non_tray_item_count_found(client):
    # Arrange
    params = NonTrayItemsCountParams(building_id=1, size_class_id=[1])

    # Act and Assert
    response = client.get("/non_tray_items/count", params=params)
    assert response.status_code == 200


def test_get_non_tray_item_count_building_not_found(client):
    # Arrange
    params = NonTrayItemsCountParams(building_id=999, size_class_id=[1])

    # Act and Assert
    response = client.get("/non_tray_items/count", params=params)
    assert response.status_code == 404
    assert response.json()["detail"] == "Building not found"


def test_get_non_tray_item_count_size_class_not_found(client):
    # Arrange
    params = NonTrayItemsCountParams(building_id=1, size_class_id=[999])

    # Act and Assert
    response = client.get("/non_tray_items/count", params=params)
    assert response.status_code == 404
    assert response.json()["detail"] == "Size class not found"


def test_get_non_tray_item_count_invalid_params(client):
    # Arrange
    params = NonTrayItemsCountParams(building_id="abc", size_class_id=[1])

    # Act and Assert
    response = client.get("/non_tray_items/count", params=params)
    assert response.status_code == 422


def test_get_non_tray_item_count_pagination(client):
    # Arrange
    params = NonTrayItemsCountParams(building_id=1, size_class_id=[1])

    # Act and Assert
    response = client.get("/non_tray_items/count", params=params)
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
