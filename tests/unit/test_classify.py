import json
from pathlib import Path

import pytest

from chargecheck.llm.classify import (
    accuracy,
    build_messages,
    classify,
    find_leaks,
    parse_label,
)
from chargecheck.llm.gateway import FakeLLM
from chargecheck.llm.prompts import versions

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("docs", "docs"),
        ("PERSONAL", "personal"),
        ("off-topic", "off_topic"),
        ("Off Topic.", "off_topic"),
        ("I think docs", "docs"),
        ("docs personal", "invalid"),
        ("unknown", "invalid"),
        ("", "invalid"),
    ],
)
def test_parse_label(reply, expected):
    assert parse_label(reply) == expected


def test_build_messages():
    messages = build_messages("Router instructions", "  What are my charges?  ")
    assert messages[0]["content"] == "Router instructions"
    assert messages[1]["content"] == "<question>\nWhat are my charges?\n</question>"


@pytest.mark.asyncio
async def test_classify_records_metadata():
    fake = FakeLLM(script=["docs"])
    label, result = await classify(fake, "Classify.", "classify_v1", "ATM charges?")
    assert label == "docs"
    assert result.text == "docs"
    assert fake.seen[0]["purpose"] == "classify"
    assert fake.seen[0]["prompt_version"] == "classify_v1"
    assert fake.seen[0]["temperature"] == 0


def test_accuracy():
    rows = [
        {"label": "docs", "got": "docs"},
        {"label": "personal", "got": "docs"},
        {"label": "off_topic", "got": "off_topic"},
    ]
    assert accuracy(rows) == pytest.approx(2 / 3)
    assert accuracy([]) == 0


def test_find_leaks():
    assert find_leaks("Example: What is my balance?", ["What is my balance?"])
    assert not find_leaks("Classify banking questions.", ["What is my balance?"])


def test_prompt_versions_sorted():
    found = versions(ROOT / "prompts", "classify")
    assert found == [
        "classify_v1",
        "classify_v2",
        "classify_v3",
        "classify_v4",
    ]


def test_testset_has_twenty_valid_rows():
    path = ROOT / "eval" / "prompt_testset.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 20
    assert all(row["label"] in {"docs", "personal", "off_topic"} for row in rows)
    assert all("TODO" not in row["question"] for row in rows)


def test_three_prompt_files_exist():
    found = versions(ROOT / "prompts", "classify")
    assert len(found) >= 4
