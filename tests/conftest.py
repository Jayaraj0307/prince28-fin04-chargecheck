import json
import os

import pytest
from fastapi.testclient import TestClient

from chargecheck.api.main import create_app
from chargecheck.config import Settings

# Tiny fake records: tests never depend on your real data file.
SAMPLE = [
    {"id": "001", "title": "Alpha guideline", "year": 2023},
    {"id": "002", "title": "Beta circular", "year": 2024},
    {"id": "003", "title": "Gamma notice", "year": 2025},
]


@pytest.fixture
def data_file(tmp_path):
    path = tmp_path / "records.json"
    path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    return path


@pytest.fixture
def client(data_file):
    settings = Settings(app_env="ci", data_file=data_file)
    with TestClient(create_app(settings)) as c:  # "with" runs startup (loads records)
        yield c


@pytest.fixture
def database_url():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    return url
