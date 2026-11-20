import pytest
from pydantic import ValidationError

from chargecheck.config import Settings


def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_when_database_is_available(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["checks"]["database"] is True


def test_list_documents_paginates(client):
    response = client.get("/v1/documents/", params={"limit": 2})
    body = response.json()

    assert response.status_code == 200
    assert body["total"] >= 2
    assert len(body["items"]) == 2


def test_search_filters_documents(client):
    response = client.get("/v1/documents/", params={"q": "Indian Bank"})

    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


def test_get_document_found(client):
    response = client.get("/v1/documents/1")

    assert response.status_code == 200
    assert response.json()["title"] == "Indian Bank"


def test_missing_document_is_404(client):
    response = client.get("/v1/documents/999999")
    assert response.status_code == 404


def test_bad_limit_is_422(client):
    response = client.get("/v1/documents/", params={"limit": 0})
    assert response.status_code == 422


def test_request_id_is_echoed(client):
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"


def test_app_refuses_to_start_without_app_env(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
