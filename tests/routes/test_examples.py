from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_get_examples_root():
    response = client.get("/examples")
    assert response.status_code == 200
    assert response.json() == {"message": "Examples API"}

def test_examples_get_numbers():
    response = client.get("/examples/numbers/33")
    assert response.status_code == 200
    assert response.json() == {"number":33}
