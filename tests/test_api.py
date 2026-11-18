from fastapi.testclient import TestClient

from chargecheck.api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200


def test_list_documents():
    response = client.get("/v1/documents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_document():
    response = client.get("/v1/documents/1")
    assert response.status_code == 200
    assert response.json()["external_id"] == "001"


def test_document_not_found():
    response = client.get("/v1/documents/999999")
    assert response.status_code == 404
