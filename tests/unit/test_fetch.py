import asyncio
import json

import httpx
import pytest

from chargecheck.ingest.fetch import (
    RETRYABLE,
    USER_AGENT,
    DownloadError,
    HostGate,
    Manifest,
    Robots,
    Source,
    backoff_delay,
    fetch_all,
    fetch_one,
    file_stem,
    make_client,
    pick_ext,
    read_sources,
    retry_after_seconds,
    slug,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_slug():
    assert slug("South Indian Bank Charges!") == "south-indian-bank-charges"


def test_file_stem_is_stable():
    url = "https://example.com/charges.pdf"
    assert file_stem(url) == file_stem(url)


def test_pick_ext_from_url():
    assert pick_ext("https://example.com/a.pdf", "") == ".pdf"


def test_pick_ext_from_content_type():
    assert pick_ext("https://example.com/a", "application/pdf") == ".pdf"


def test_backoff_delay_is_bounded():
    assert 0 <= backoff_delay(2, base=1, cap=5) <= 4


def test_retry_after_seconds_numeric():
    assert retry_after_seconds("12") == 12.0


def test_retry_after_seconds_invalid():
    assert retry_after_seconds("not-a-date") is None


def test_read_sources_and_remove_duplicates(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text(
        "url,source,licence,title\n"
        "https://example.com/a.pdf,Bank,Public disclosure,A\n"
        "https://example.com/a.pdf,Bank,Public disclosure,A\n",
        encoding="utf-8",
    )

    sources = read_sources(path)

    assert len(sources) == 1
    assert sources[0].source == "Bank"


def test_read_sources_rejects_invalid_url(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text(
        "url,source,licence\nftp://example.com/a,Bank,Public disclosure\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        read_sources(path)


def test_read_sources_requires_licence(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text(
        "url,source,licence\nhttps://example.com/a.pdf,Bank,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        read_sources(path)


def test_manifest_loads_latest_record(tmp_path):
    path = tmp_path / "manifest.jsonl"
    path.write_text(
        json.dumps({"url": "https://example.com/a", "status": "failed"})
        + "\n"
        + json.dumps({"url": "https://example.com/a", "status": "downloaded"})
        + "\n",
        encoding="utf-8",
    )

    manifest = Manifest(path)

    assert manifest.records["https://example.com/a"]["status"] == "downloaded"


def test_manifest_done_requires_file(tmp_path):
    manifest = Manifest(tmp_path / "manifest.jsonl")
    manifest.add(
        {
            "url": "https://example.com/a",
            "status": "downloaded",
            "path": "data/raw/a.pdf",
        }
    )

    assert not manifest.done("https://example.com/a", tmp_path)


def test_manifest_done_when_file_exists(tmp_path):
    target = tmp_path / "data/raw/a.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"pdf")

    manifest = Manifest(tmp_path / "manifest.jsonl")
    manifest.add(
        {
            "url": "https://example.com/a",
            "status": "downloaded",
            "path": "data/raw/a.pdf",
        }
    )

    assert manifest.done("https://example.com/a", tmp_path)


def test_make_client_sets_user_agent():
    client = make_client()

    assert client.headers["User-Agent"] == USER_AGENT
    assert client.follow_redirects

    asyncio.run(client.aclose())


@pytest.mark.anyio
async def test_robots_allows_and_caches_robots_file():
    calls = []

    def handler(request):
        calls.append(str(request.url))

        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: examate-student-bot\nAllow: /\n",
            )

        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        robots = Robots(client)

        assert (await robots.check("https://example.com/a"))[0]
        assert (await robots.check("https://example.com/b"))[0]

    assert calls.count("https://example.com/robots.txt") == 1


@pytest.mark.anyio
async def test_robots_blocks_disallowed_path():
    def handler(request):
        return httpx.Response(
            200,
            text="User-agent: examate-student-bot\nDisallow: /private\n",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        robots = Robots(client)
        allowed, _ = await robots.check("https://example.com/private/a.pdf")

    assert not allowed


@pytest.mark.anyio
async def test_host_gate_waits_between_requests():
    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    gate = HostGate(2.0, fake_sleep)

    await gate.wait("example.com")
    await gate.wait("example.com")

    assert waits


@pytest.mark.anyio
async def test_fetch_all_downloads_and_resumes(tmp_path):
    calls = []

    def handler(request):
        calls.append(request.url.path)

        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: *\nAllow: /\n",
            )

        return httpx.Response(
            200,
            headers={"Content-Type": "text/plain"},
            content=b"sample bank disclosure",
        )

    source = Source(
        "https://example.com/disclosure.txt",
        "Test Bank",
        "Public disclosure",
        "Test",
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        first = await fetch_all(
            [source],
            root=tmp_path,
            client=client,
            per_host_delay=0,
            sleep=lambda _: asyncio.sleep(0),
        )

        second = await fetch_all(
            [source],
            root=tmp_path,
            client=client,
            per_host_delay=0,
            sleep=lambda _: asyncio.sleep(0),
        )

    assert first["downloaded"] == 1
    assert second["skipped"] == 1
    assert len(list((tmp_path / "data/raw").rglob("*.txt"))) == 1
    assert not list((tmp_path / "data/raw").rglob("*.part"))


@pytest.mark.anyio
async def test_fetch_one_blocks_robots_disallowed_source(tmp_path):
    def handler(request):
        return httpx.Response(
            200,
            text="User-agent: examate-student-bot\nDisallow: /\n",
        )

    source = Source(
        "https://example.com/private.pdf",
        "Test Bank",
        "Public disclosure",
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        record = await fetch_one(
            client,
            source,
            root=tmp_path,
            raw_dir=tmp_path / "data/raw",
            robots=Robots(client),
            gate=HostGate(0, lambda _: asyncio.sleep(0)),
            slots=asyncio.Semaphore(1),
            max_attempts=1,
            sleep=lambda _: asyncio.sleep(0),
        )

    assert record["status"] == "blocked"


@pytest.mark.anyio
async def test_fetch_one_rejects_html_disguised_as_pdf(tmp_path):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: *\nAllow: /\n",
            )

        return httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            content=b"<html>",
        )

    source = Source(
        "https://example.com/disclosure.pdf",
        "Test Bank",
        "Public disclosure",
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        record = await fetch_one(
            client,
            source,
            root=tmp_path,
            raw_dir=tmp_path / "data/raw",
            robots=Robots(client),
            gate=HostGate(0, lambda _: asyncio.sleep(0)),
            slots=asyncio.Semaphore(1),
            max_attempts=1,
            sleep=lambda _: asyncio.sleep(0),
        )

    assert record["status"] == "failed"
    assert not list((tmp_path / "data/raw").rglob("*.part"))


def test_retryable_status_codes():
    assert {408, 425, 429, 500, 502, 503, 504} == RETRYABLE


def test_download_error_keeps_status_code():
    error = DownloadError("HTTP 503", code=503, retry_after=5)

    assert error.code == 503
    assert error.retry_after == 5
