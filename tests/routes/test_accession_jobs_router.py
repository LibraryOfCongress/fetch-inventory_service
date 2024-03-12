import logging
import pytest
from fastapi import status
from sqlalchemy.exc import IntegrityError

from tests.fixtures.configtest import init_db, test_database, client, session
from tests.fixtures.accession_jobs_fixture import (
    ACCESSION_JOBS_SINGLE_RECORD_RESPONSE,
    ACCESSION_JOBS_PAGE_DATA_RESPONSE,
    ACCESSION_JOBS_SIZE_DATA_RESPONSE,
    CREATE_ACCESSION_JOBS_SINGLE_RECORD,
    UPDATED_ACCESSION_JOBS_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_accession_jobs_router")


def test_get_all_accession_jobs(client, test_database):
    response = client.get("/accession-jobs")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ACCESSION_JOBS_SINGLE_RECORD_RESPONSE


def test_get_accession_jobs_by_page(client):
    response = client.get("/accession-jobs?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("page") == 1


def test_get_accession_jobs_by_page_size(client):
    response = client.get("/accession-jobs?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("size") == 10


def test_get_all_accession_jobs_not_found(client):
    response = client.get("/accession-jobs/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Accession Job ID 999 Not Found"}


def test_get_accession_job_by_id(client):
    response = client.get("/accession-jobs/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == ACCESSION_JOBS_SINGLE_RECORD_RESPONSE.get(
        "items"
    )[0].get("id")


# TODO: Add test cases for create
def test_create_accession_job_record(client):
    pass


# TODO: Add test cases for update
def test_patch_accession_job_record(client):
    pass


def test_update_accession_job_record_not_found(client):
    response = client.patch(
        "/accession-jobs/999", json=UPDATED_ACCESSION_JOBS_SINGLE_RECORD
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Accession Job ID 999 Not Found"


# TODO: Add test cases for delete
def test_delete_accession_job_record_success(client):
    pass


def test_delete_accession_job_record_not_found(client):
    response = client.delete("/accession-jobs/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Accession Job ID 999 Not Found"


def test_get_accession_job_list_with_queue_true(client):
    response = client.get("/accession-jobs/?queue=True")
    assert response.status_code == 200
    # Add more assertions as needed


def test_get_accession_job_list_with_queue_false(client):
    response = client.get("/accession-jobs/?queue=False")
    assert response.status_code == 200
    # Add more assertions as needed


def test_get_accession_job_list_without_queue(client):
    response = client.get("/accession-jobs/")
    assert response.status_code == 200
    assert "items" in response.json()


def test_get_accession_job_list_with_queue(client):
    response = client.get("/accession-jobs/?queue=True")
    assert response.status_code == 200
    assert "items" in response.json()

