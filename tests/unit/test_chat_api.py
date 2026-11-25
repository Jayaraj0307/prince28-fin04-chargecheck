def test_chat_json(client):
    response = client.post(
        "/v1/chat",
        json={"message": "Hello", "stream": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "A fake answer."
    assert data["provider"] == "fake"


def test_chat_stream(client):
    response = client.post(
        "/v1/chat",
        json={"message": "Hello", "stream": True},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: delta" in response.text
    assert "event: done" in response.text


def test_chat_rejects_empty_message(client):
    response = client.post(
        "/v1/chat",
        json={"message": "", "stream": False},
    )

    assert response.status_code == 422


def test_chat_rejects_missing_message(client):
    response = client.post("/v1/chat", json={})

    assert response.status_code == 422


def test_usage(client):
    response = client.get("/v1/usage")

    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 30
    assert data["calls"] == 0
    assert data["total_cost_inr"] == 0


def test_usage_custom_days(client):
    response = client.get("/v1/usage?days=7")

    assert response.status_code == 200
    assert response.json()["days"] == 7


def test_usage_rejects_invalid_days(client):
    response = client.get("/v1/usage?days=100")

    assert response.status_code == 422
