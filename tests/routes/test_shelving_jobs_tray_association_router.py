import logging
from fastapi import status

from tests.fixtures.configtest import client, session
from tests.fixtures.shelving_jobs_tray_association_fixture import (
    SHELVING_JOBS_TRAY_ASSOCIATION_SINGLE_RECORD_RESPONSE,
    SHELVING_JOBS_TRAY_ASSOCIATION_PAGE_DATA_RESPONSE,
    SHELVING_JOBS_TRAY_ASSOCIATION_SIZE_DATA_RESPONSE,
    CREATE_SHELVING_JOBS_TRAY_ASSOCIATION_SINGLE_RECORD,
    UPDATED_SHELVING_JOBS_TRAY_ASSOCIATION_SINGLE_RECORD,
)

LOGGER = logging.getLogger("tests.routes.test_shelving_jobs_router")


def test_get_all_shelving_jobs_tray_association(client):
    response = client.get("/shelving-jobs/tray-association")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELVING_JOBS_TRAY_ASSOCIATION_SINGLE_RECORD_RESPONSE


def test_get_shelving_jobs_tray_association_by_page(client):
    response = client.get("/shelving-jobs/tray-association?page=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELVING_JOBS_TRAY_ASSOCIATION_PAGE_DATA_RESPONSE


def test_get_shelving_jobs_tray_association_by_page_size(client):
    response = client.get("/shelving-jobs/tray-association?size=10")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SHELVING_JOBS_TRAY_ASSOCIATION_SIZE_DATA_RESPONSE


def test_get_all_shelving_jobs_tray_association_not_found(client):
    response = client.get("/shelving-jobs/tray-association/999/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_get_shelving_job_tray_association_by_id(client):
    response = client.get("/shelving-jobs/tray-association/1/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get(
        "id"
    ) == SHELVING_JOBS_TRAY_ASSOCIATION_SINGLE_RECORD_RESPONSE.get("items")[0].get("id")


# TODO: Add test cases for create
def test_create_shelving_job_tray_association_record(client):
    pass


# TODO: Add test cases for update
def test_update_shelving_job_tray_association_record(client):
    pass


# TODO: Add test cases for update
def test_update_shelving_job_tray_association_record_not_found(client):
    pass


# TODO: Add test cases for delete
def test_delete_shelving_job_tray_association_record_success(client):
    pass


def test_delete_shelving_job_tray_association_record_not_found(client):
    response = client.delete("/shelving-jobs/tray-association/999/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("detail") == "Not Found"
