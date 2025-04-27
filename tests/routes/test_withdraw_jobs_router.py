import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.withdraw_jobs_fixture import (
    WITHDRAW_JOBS_SINGLE_RECORD_RESPONSE,
    WITHDRAW_JOBS_PAGE_DATA_RESPONSE,
    WITHDRAW_JOBS_SIZE_DATA_RESPONSE,
    CREATE_WITHDRAW_JOBS_SINGLE_RECORD,
    UPDATED_WITHDRAW_JOBS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_withdraw_jobs_router")


def test_get_all_withdraw_jobs(client):
    response = client.get("/withdraw-jobs")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == WITHDRAW_JOBS_SINGLE_RECORD_RESPONSE


def test_get_withdraw_jobs_by_page(client):
    response = client.get("/withdraw-jobs?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == WITHDRAW_JOBS_PAGE_DATA_RESPONSE


def test_get_withdraw_jobs_by_page_size(client):
    response = client.get("/withdraw-jobs?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == WITHDRAW_JOBS_SIZE_DATA_RESPONSE


def test_get_all_withdraw_jobs_not_found(client):
    response = client.get("/withdraw-jobs/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Verification Job ID 999 Not Found"}


def test_get_withdraw_job_by_id(client):
    response = client.get("/withdraw-jobs/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == WITHDRAW_JOBS_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("id")


def test_create_withdraw_job_record(client):
    response = client.post(
        "/withdraw-jobs", json=CREATE_WITHDRAW_JOBS_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("trayed") == CREATE_WITHDRAW_JOBS_SINGLE_RECORD.get(
        "trayed"
    )
    assert response.json().get("status") == CREATE_WITHDRAW_JOBS_SINGLE_RECORD.get(
        "status"
    )
    assert response.json().get(
        "run_time"
    ) == CREATE_WITHDRAW_JOBS_SINGLE_RECORD.get("run_time")
    assert response.json().get(
        "accession_job_id"
    ) == CREATE_WITHDRAW_JOBS_SINGLE_RECORD.get("accession_job_id")
    assert response.json().get(
        "container_type_id"
    ) == CREATE_WITHDRAW_JOBS_SINGLE_RECORD.get("container_type_id")
    assert response.json().get(
        "owner_id"
    ) == CREATE_WITHDRAW_JOBS_SINGLE_RECORD.get("owner_id")
    assert response.json().get("user_id") == CREATE_WITHDRAW_JOBS_SINGLE_RECORD.get(
        "user_id"
    )


def test_patch_withdraw_job_record(client):
    response = client.patch(
        "/withdraw-jobs/1", json=UPDATED_WITHDRAW_JOBS_SINGLE_RECORD
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("trayed") == UPDATED_WITHDRAW_JOBS_SINGLE_RECORD.get(
        "trayed"
    )
    assert response.json().get(
        "run_time"
    ) == UPDATED_WITHDRAW_JOBS_SINGLE_RECORD.get("run_time")
    assert response.json().get("status") == UPDATED_WITHDRAW_JOBS_SINGLE_RECORD.get(
        "status"
    )


def test_update_withdraw_job_record_not_found(client):
    response = client.patch(
        "/withdraw-jobs/999", json=UPDATED_WITHDRAW_JOBS_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Verification Job ID 999 Not Found"


def test_delete_withdraw_job_record_success(client):
    response = client.post(
        "/withdraw-jobs/", json=CREATE_WITHDRAW_JOBS_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_201_CREATED

    withdraw_job_id = response.json().get("id")

    response = client.delete(f"/withdraw-jobs/{withdraw_job_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == (f"Verification Job ID {withdraw_job_id} Deleted "
                                             f"Successfully")


def test_delete_withdraw_job_record_not_found(client):
    response = client.delete("/withdraw-jobs/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Verification Job ID 999 Not Found"
