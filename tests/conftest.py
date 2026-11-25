import json
import os

import pytest
from fastapi.testclient import TestClient

from chargecheck.api.deps import get_gateway, get_usage_repo
from chargecheck.api.main import create_app
from chargecheck.config import Settings
from chargecheck.llm.gateway import FakeLLM, LLMGateway

SAMPLE = [
    {"id": "001", "title": "Alpha guideline", "year": 2023},
    {"id": "002", "title": "Beta circular", "year": 2024},
    {"id": "003", "title": "Gamma notice", "year": 2025},
]


class FakeUsage:
    async def by_day(self, days: int = 30) -> list[dict]:
        return []


@pytest.fixture
def data_file(tmp_path):
    path = tmp_path / "records.json"
    path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    return path


@pytest.fixture
def client(data_file):
    settings = Settings(app_env="ci", data_file=data_file)
    app = create_app(settings)

    app.dependency_overrides[get_gateway] = lambda: LLMGateway([FakeLLM()])
    app.dependency_overrides[get_usage_repo] = lambda: FakeUsage()

    with TestClient(app) as c:
        yield c


@pytest.fixture
def database_url():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    return url
