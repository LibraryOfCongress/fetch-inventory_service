import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.verification_jobs_fixture import (
    VERIFICATION_JOBS_SINGLE_RECORD_RESPONSE,
    VERIFICATION_JOBS_PAGE_DATA_RESPONSE,
    VERIFICATION_JOBS_SIZE_DATA_RESPONSE,
    CREATE_VERIFICATION_JOBS_SINGLE_RECORD,
    UPDATED_VERIFICATION_JOBS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_verification_jobs_router")


def test_get_all_verification_jobs(client):
    response = client.get("/verification-jobs")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == VERIFICATION_JOBS_SINGLE_RECORD_RESPONSE


def test_get_verification_jobs_by_page(client):
    response = client.get("/verification-jobs?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == VERIFICATION_JOBS_PAGE_DATA_RESPONSE


def test_get_verification_jobs_by_page_size(client):
    response = client.get("/verification-jobs?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == VERIFICATION_JOBS_SIZE_DATA_RESPONSE


def test_get_all_verification_jobs_not_found(client):
    response = client.get("/verification-jobs/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_verification_job_by_id(client):
    response = client.get("/verification-jobs/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == VERIFICATION_JOBS_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("id")


def test_create_verification_job_record(client):
    response = client.post(
        "/verification-jobs", json=CREATE_VERIFICATION_JOBS_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("trayed") == CREATE_VERIFICATION_JOBS_SINGLE_RECORD.get(
        "trayed"
    )
    assert response.json().get("status") == CREATE_VERIFICATION_JOBS_SINGLE_RECORD.get(
        "status"
    )
    assert response.json().get(
        "run_time"
    ) == CREATE_VERIFICATION_JOBS_SINGLE_RECORD.get("run_time")
    assert response.json().get(
        "accession_job_id"
    ) == CREATE_VERIFICATION_JOBS_SINGLE_RECORD.get("accession_job_id")
    assert response.json().get(
        "container_type_id"
    ) == CREATE_VERIFICATION_JOBS_SINGLE_RECORD.get("container_type_id")
    assert response.json().get(
        "owner_id"
    ) == CREATE_VERIFICATION_JOBS_SINGLE_RECORD.get("owner_id")
    assert response.json().get("user_id") == CREATE_VERIFICATION_JOBS_SINGLE_RECORD.get(
        "user_id"
    )


def test_patch_verification_job_record(client):
    response = client.patch(
        "/verification-jobs/1", json=UPDATED_VERIFICATION_JOBS_SINGLE_RECORD
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("trayed") == UPDATED_VERIFICATION_JOBS_SINGLE_RECORD.get(
        "trayed"
    )
    assert response.json().get(
        "run_time"
    ) == UPDATED_VERIFICATION_JOBS_SINGLE_RECORD.get("run_time")
    assert response.json().get("status") == UPDATED_VERIFICATION_JOBS_SINGLE_RECORD.get(
        "status"
    )


def test_update_verification_job_record_not_found(client):
    response = client.patch(
        "/verification-jobs/999", json=UPDATED_VERIFICATION_JOBS_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


def test_delete_verification_job_record_success(client):
    response = client.post(
        "/verification-jobs/", json=CREATE_VERIFICATION_JOBS_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_201_CREATED

    response = client.delete(f"/verification-jobs/{response.json().get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("status_code") == 204
    assert response.json().get("detail") == "No Content"


def test_delete_verification_job_record_not_found(client):
    response = client.delete("/verification-jobs/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
