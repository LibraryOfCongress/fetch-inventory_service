import pytest
from fastapi import status
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
