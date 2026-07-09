from __future__ import annotations

import pytest

from src.insightdf.llm import _extract_json_object


def test_extracts_plain_json() -> None:
    payload = '{"analysis_type":"scalar","sql":"SELECT 1","reasoning":"ok"}'
    assert _extract_json_object(payload) == payload


def test_extracts_json_from_wrapped_response() -> None:
    wrapped = 'Based on the schema:\n```json\n{"analysis_type":"scalar","sql":"SELECT 1","reasoning":"ok"}\n```'
    assert _extract_json_object(wrapped) == '{"analysis_type":"scalar","sql":"SELECT 1","reasoning":"ok"}'


def test_raises_when_no_json_object_exists() -> None:
    with pytest.raises(ValueError):
        _extract_json_object("This is only prose.")
