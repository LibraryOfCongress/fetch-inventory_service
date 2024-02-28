import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.shelving_jobs_fixture import (
    SHELVING_JOBS_SINGLE_RECORD_RESPONSE,
    SHELVING_JOBS_PAGE_DATA_RESPONSE,
    SHELVING_JOBS_SIZE_DATA_RESPONSE,
    CREATE_SHELVING_JOBS_SINGLE_RECORD,
    UPDATED_SHELVING_JOBS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_shelving_jobs_router")


def test_get_all_shelving_jobs(client):
    response = client.get("/shelving-jobs")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELVING_JOBS_SINGLE_RECORD_RESPONSE


def test_get_shelving_jobs_by_page(client):
    response = client.get("/shelving-jobs?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("page") == 1


def test_get_shelving_jobs_by_page_size(client):
    response = client.get("/shelving-jobs?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("size") == 10


def test_get_all_shelving_jobs_not_found(client):
    response = client.get("/shelving-jobs/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_shelving_job_by_id(client):
    response = client.get("/shelving-jobs/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == SHELVING_JOBS_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("id")


# TODO: Add test cases for create
def test_create_shelving_job_record(client):
    pass


# TODO: Add test cases for update
def test_patch_shelving_job_record(client):
    pass


def test_update_shelving_job_record_not_found(client):
    response = client.patch(
        "/shelving-jobs/999", json=UPDATED_SHELVING_JOBS_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"


# TODO: Add test cases for delete
def test_delete_shelving_job_record_success(client):
    pass


def test_delete_shelving_job_record_not_found(client):
    response = client.delete("/shelving-jobs/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
