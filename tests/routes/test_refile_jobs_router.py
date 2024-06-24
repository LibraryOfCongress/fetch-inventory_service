import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.refile_jobs_fixture import (
    REFILE_JOBS_SINGLE_RECORD_RESPONSE,
    REFILE_JOBS_PAGE_DATA_RESPONSE,
    REFILE_JOBS_SIZE_DATA_RESPONSE,
    UPDATED_REFILE_JOBS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_refile_jobs_router")


def test_get_all_refile_jobs(client):
    response = client.get("/refile-jobs")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == REFILE_JOBS_SINGLE_RECORD_RESPONSE


def test_get_refile_jobs_by_page(client):
    response = client.get("/refile-jobs?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == REFILE_JOBS_PAGE_DATA_RESPONSE


def test_get_refile_jobs_by_page_size(client):
    response = client.get("/refile-jobs?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == REFILE_JOBS_SIZE_DATA_RESPONSE


def test_get_all_refile_jobs_not_found(client):
    response = client.get("/refile-jobs/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Refile Job ID 999 Not Found"}


def test_get_refile_job_by_id(client):
    response = client.get("/refile-jobs/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == REFILE_JOBS_SINGLE_RECORD_RESPONSE.get("items")[
        0
    ].get("id")


def test_create_refile_job_record(client):
    response = client.post(
        "/refile-jobs",
        json={"assigned_user_id": 1, "run_time": "03:25:15", "status": "Created"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("assigned_user_id") == 1
    assert response.json().get("run_time") == "03:25:15"
    assert response.json().get("status") == "Created"


def test_update_refile_job_record(client):
    response = client.post(
        "/refile-jobs",
        json={"assigned_user_id": 1, "run_time": "03:25:15", "status": "Created"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("assigned_user_id") == 1
    assert response.json().get("run_time") == "03:25:15"
    assert response.json().get("status") == "Created"

    response = client.patch(
        f"/refile-jobs/{response.json().get('id')}",
        json={"run_time": "03:30:00", "status": "Paused"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("run_time") == "03:30:00"
    assert response.json().get("status") == "Paused"


def test_update_refile_job_record_not_found(client):
    response = client.patch("/refile-jobs/999", json=UPDATED_REFILE_JOBS_SINGLE_RECORD)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Refile Job ID 999 Not Found"


def test_delete_refile_job_record_success(client):
    response = client.post(
        "/refile-jobs",
        json={"assigned_user_id": 1, "run_time": "03:25:15", "status": "Created"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("assigned_user_id") == 1
    assert response.json().get("run_time") == "03:25:15"
    assert response.json().get("status") == "Created"

    response = client.delete(f"/refile-jobs/{response.json().get('id')}")
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_refile_job_record_not_found(client):
    response = client.delete("/refile-jobs/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Refile Job ID 999 Not Found"


def test_add_item_success(client):
    response = client.post(
        "/refile-jobs",
        json={"assigned_user_id": 1, "run_time": "03:25:15", "status": "Created"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("assigned_user_id") == 1
    assert response.json().get("run_time") == "03:25:15"
    assert response.json().get("status") == "Created"

    refile_job_id = response.json().get("id")

    response = client.post(
        f"/refile-jobs/{refile_job_id}/add_item/1",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("items")[0].get("id") == 1


def test_refile_job_not_found(client):
    response = client.post(
        f"/refile-jobs/999/add_item/1",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Refile Job ID 999 Not Found"


def test_item_not_found(client):
    response = client.post(
        f"/refile-jobs/1/add_item/999",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Item ID 999 Not Found"


def test_remove_item_from_refile_job(client):
    # Test case when refile job and item exist
    response = client.delete(f"/refile-jobs/5/remove_item/1")
    assert response.status_code == status.HTTP_200_OK


def test_remove_item_from_refile_job_not_found(client):
    # Test case when refile job does not exist
    response = client.delete("/999/remove_item/1")
    assert response.status_code == 404
    assert response.json().get("detail") == "Not Found"


def test_remove_item_from_refile_job_item_not_found(client):
    # Test case when item does not exist
    response = client.delete("/1/remove_item/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_add_non_tray_item_to_refile_job(client):
    response = client.post(
        "/refile-jobs",
        json={"assigned_user_id": 1, "run_time": "03:25:15", "status": "Created"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("assigned_user_id") == 1
    assert response.json().get("run_time") == "03:25:15"
    assert response.json().get("status") == "Created"

    refile_job_id = response.json().get("id")

    response = client.post(
        f"/refile-jobs/{refile_job_id}/add_non_tray_item/1",
    )

    assert response.status_code == status.HTTP_200_OK


def test_remove_non_tray_item_from_refile_job(client):
    # Test case when refile job and item exist
    response = client.delete(f"/refile-jobs/6/remove_non_tray_item/1")
    assert response.status_code == status.HTTP_200_OK


def test_remove_non_tray_item_from_refile_job_not_found(client):
    # Test case when refile job does not exist
    response = client.delete("/999/remove_non_tray_item/1")
    assert response.status_code == 404
    assert response.json().get("detail") == "Not Found"


def test_remove_non_tray_item_from_refile_job_item_not_found(client):
    # Test case when item does not exist
    response = client.delete("/1/remove_non_tray_item/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
