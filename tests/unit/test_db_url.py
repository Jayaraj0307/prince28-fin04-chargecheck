
from chargecheck.db.url import to_asyncpg_url


def test_postgres_url_converts_to_asyncpg():
    result = to_asyncpg_url("postgresql://user:pass@localhost:5432/testdb")
    assert result == "postgresql+asyncpg://user:pass@localhost:5432/testdb"


def test_neon_url_removes_channel_binding_and_requires_ssl():
    result = to_asyncpg_url(
        "postgresql://user:pass@host:5432/testdb?sslmode=require&channel_binding=require"
    )
    assert result == "postgresql+asyncpg://user:pass@host:5432/testdb?ssl=require"


def test_asyncpg_url_stays_asyncpg():
    result = to_asyncpg_url(
        "postgresql+asyncpg://user:pass@localhost:5432/testdb"
    )
    assert result == "postgresql+asyncpg://user:pass@localhost:5432/testdb"


def test_sslmode_disable_does_not_add_ssl():
    result = to_asyncpg_url(
        "postgresql://user:pass@localhost:5432/testdb?sslmode=disable"
    )
    assert result == "postgresql+asyncpg://user:pass@localhost:5432/testdb"
