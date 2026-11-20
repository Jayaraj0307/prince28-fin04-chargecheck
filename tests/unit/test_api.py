def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"] == "chargecheck"
    assert response.json()["version"] == "dev"


def test_health_supports_head_request(client):
    response = client.head("/health")
    assert response.status_code == 200


def test_health_includes_git_sha(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert "version" in response.json()
