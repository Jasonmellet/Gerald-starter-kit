"""Tests for structured_output: code fence stripping, JSON extraction, repair flow, validation."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.schemas import OpportunityScores, ProspectSummary, SignalExtract
from app.constants import SignalType
from app.structured_output import (
    strip_code_fences,
    extract_first_json,
    normalize_and_parse,
    get_structured,
    StructuredOutputStats,
)


# --- Code fence stripping ---


def test_strip_code_fences_plain_json_unchanged():
    text = '{"a": 1}'
    assert strip_code_fences(text) == '{"a": 1}'


def test_strip_code_fences_json_block():
    text = '```json\n{"a": 1}\n```'
    assert strip_code_fences(text) == '{"a": 1}'


def test_strip_code_fences_no_lang():
    text = '```\n[1, 2]\n```'
    assert strip_code_fences(text) == "[1, 2]"


def test_strip_code_fences_empty_returns_stripped():
    assert strip_code_fences("  \n  ") == ""


# --- JSON extraction from mixed text ---


def test_extract_first_json_object():
    text = 'Here is the result: {"x": 1} and more'
    assert extract_first_json(text) == '{"x": 1}'


def test_extract_first_json_array():
    text = 'Result: [1, 2, 3] done'
    assert extract_first_json(text) == "[1, 2, 3]"


def test_extract_first_json_nested():
    text = 'Out: {"a": [1, 2]}'
    assert extract_first_json(text) == '{"a": [1, 2]}'


def test_extract_first_json_returns_none_for_no_brackets():
    assert extract_first_json("no json here") is None
    assert extract_first_json("") is None


# --- normalize_and_parse ---


def test_normalize_and_parse_direct():
    data, used = normalize_and_parse('{"a": 1}')
    assert data == {"a": 1}
    assert used is False


def test_normalize_and_parse_fenced():
    raw = '```json\n{"a": 1}\n```'
    data, used = normalize_and_parse(raw)
    assert data == {"a": 1}
    assert used is True


def test_normalize_and_parse_mixed_text():
    raw = 'The response is: {"a": 1}'
    data, used = normalize_and_parse(raw)
    assert data == {"a": 1}
    assert used is True


def test_normalize_and_parse_invalid_returns_none():
    data, _ = normalize_and_parse("not json at all")
    assert data is None


# --- get_structured: schema validation and failure handling ---


def test_get_structured_valid_object(tmp_path):
    raw = '{"role_guess": "CMO", "company_guess": "Acme", "summary": "Test", "fit_notes": "Good"}'
    result, stats = get_structured(
        raw,
        schema_class=ProspectSummary,
        expect_list=False,
        step_name="test",
        debug_dir=tmp_path,
    )
    assert stats.success
    assert result is not None
    assert result.role_guess == "CMO"
    assert result.summary == "Test"


def test_get_structured_valid_list(tmp_path):
    raw = '''[
        {"signal_type": "NEEDS_PIPELINE", "confidence": 0.8, "evidence_text": "We need pipeline"}
    ]'''
    result, stats = get_structured(
        raw,
        schema_class=SignalExtract,
        expect_list=True,
        step_name="test",
        debug_dir=tmp_path,
    )
    assert stats.success
    assert len(result) == 1
    assert result[0].signal_type == SignalType.NEEDS_PIPELINE


def test_get_structured_validation_failure_wrong_schema(tmp_path):
    """Valid JSON but wrong shape -> validation_failures, raw saved to debug."""
    raw = '{"wrong": "shape"}'
    result, stats = get_structured(
        raw,
        schema_class=ProspectSummary,
        expect_list=False,
        step_name="test_validation_fail",
        debug_dir=tmp_path,
    )
    assert not stats.success
    assert stats.validation_failures == 1
    assert result is None
    assert stats.raw_saved_path is not None
    assert tmp_path.joinpath(Path(stats.raw_saved_path).name).exists()


def test_get_structured_parse_failure_saves_raw(tmp_path):
    raw = "not json"
    result, stats = get_structured(
        raw,
        schema_class=ProspectSummary,
        expect_list=False,
        step_name="test_parse_fail",
        debug_dir=tmp_path,
    )
    assert not stats.success
    assert stats.parse_failures == 1
    assert result is None
    assert stats.raw_saved_path is not None


def test_get_structured_repair_flow(tmp_path):
    """When parse fails, repair_fn returns valid JSON -> success and repaired=True."""
    bad_raw = "not valid json"
    good_json = '{"urgency_score": 50, "fit_score": 50, "buyer_score": 50, "outreach_score": 50, "confidence_score": 50, "summary": "Ok"}'

    def repair_fn(_raw: str) -> str:
        return good_json

    result, stats = get_structured(
        bad_raw,
        schema_class=OpportunityScores,
        expect_list=False,
        step_name="test_repair",
        debug_dir=tmp_path,
        repair_fn=repair_fn,
    )
    assert stats.success
    assert stats.repaired
    assert stats.parse_failures == 0
    assert result is not None
    assert result.summary == "Ok"


def test_get_structured_repair_still_invalid_saves_raw(tmp_path):
    """Repair returns still-invalid text -> parse_failures, raw saved."""
    bad_raw = "not json"

    def repair_fn(_raw: str) -> str:
        return "still not json"

    result, stats = get_structured(
        bad_raw,
        schema_class=ProspectSummary,
        expect_list=False,
        step_name="test_repair_fail",
        debug_dir=tmp_path,
        repair_fn=repair_fn,
    )
    assert not stats.success
    assert result is None
    assert stats.raw_saved_path is not None
