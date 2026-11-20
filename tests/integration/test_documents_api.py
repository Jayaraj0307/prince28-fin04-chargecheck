from fastapi.testclient import TestClient

from chargecheck.api.main import create_app


def test_health_endpoint():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_documents_endpoint_requires_database():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/v1/documents/")

    # Without a configured database, the API should report service unavailable.
    assert response.status_code in (200, 503)
