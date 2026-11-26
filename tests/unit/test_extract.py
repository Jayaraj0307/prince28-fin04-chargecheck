import pytest
from pydantic import ValidationError

from chargecheck.llm.extract import DocMeta


def valid_metadata():
    return {
        "doc_kind": "guideline",
        "year": 2024,
        "language": "en",
        "summary": "This document explains savings account charges and free banking services.",
        "topics": ["ATM", "Savings", "ATM"],
        "bank": ["Indian Bank"],
        "charge_type": ["ATM withdrawal"],
        "account_variant": ["Basic Savings"],
        "effective_from": [],
    }


def test_valid_metadata():
    result = DocMeta.model_validate(valid_metadata())
    assert result.doc_kind == "guideline"
    assert result.year == 2024


def test_topics_are_lowercase_and_unique():
    result = DocMeta.model_validate(valid_metadata())
    assert result.topics == ["atm", "savings"]


def test_invalid_year_rejected():
    data = valid_metadata()
    data["year"] = 1940

    with pytest.raises(ValidationError):
        DocMeta.model_validate(data)


def test_invalid_doc_kind_rejected():
    data = valid_metadata()
    data["doc_kind"] = "unknown"

    with pytest.raises(ValidationError):
        DocMeta.model_validate(data)


def test_extra_fields_rejected():
    data = valid_metadata()
    data["source"] = "unexpected"

    with pytest.raises(ValidationError):
        DocMeta.model_validate(data)
