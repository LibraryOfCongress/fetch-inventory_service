import pytest
from fastapi import UploadFile

from app.models.batch_upload import BatchUpload
from tests.fixtures.configtest import client, session


# Test the batch_upload_location_management endpoint
def test_batch_upload_location_management(client, session):
    # Create a test file
    file = UploadFile(filename="test.xlsx", file=b"test data")

    # Send a POST request to the endpoint
    response = client.post("/location-management", files={"file": file}, data={"building_id": 1, "module_id": 1, "aisle_id": 1, "side_id": 1})

    # Assert that the response is successful
    assert response.status_code == 200

    # Assert that the batch upload was created successfully
    batch_upload = session.query(BatchUpload).first()
    assert batch_upload is not None


# Test the batch_upload_location_management endpoint with invalid file
def test_batch_upload_location_management_invalid_file(client, session):
    # Create a test file with invalid data
    file = UploadFile(filename="test.txt", file=b"invalid data")

    # Send a POST request to the endpoint
    response = client.post("/location-management", files={"file": file}, data={"building_id": 1, "module_id": 1, "aisle_id": 1, "side_id": 1})

    # Assert that the response is an error
    assert response.status_code == 400

    # Assert that the batch upload was not created
    batch_upload = session.query(BatchUpload).first()
    assert batch_upload is None


# Test the batch_upload_location_management endpoint with missing required fields
def test_batch_upload_location_management_missing_fields(client, session):
    # Send a POST request to the endpoint with missing required fields
    response = client.post("/location-management", files={"file": UploadFile(filename="test.xlsx", file=b"test data")}, data={"building_id": 1, "module_id": 1})

    # Assert that the response is an error
    assert response.status_code == 400

    # Assert that the batch upload was not created
    batch_upload = session.query(BatchUpload).first()
    assert batch_upload is None
