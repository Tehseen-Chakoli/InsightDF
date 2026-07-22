from __future__ import annotations

import pytest

from src.insightdf.sql_guard import validate_read_only_sql


def test_accepts_select_query_against_dataset() -> None:
    sql = 'SELECT COUNT(*) AS total FROM dataset WHERE "region" = \'east\''
    assert validate_read_only_sql(sql) == sql


def test_accepts_select_query_with_trailing_semicolon() -> None:
    sql = 'SELECT COUNT(*) AS total FROM dataset WHERE "region" = \'east\';'
    assert validate_read_only_sql(sql) == 'SELECT COUNT(*) AS total FROM dataset WHERE "region" = \'east\''


def test_rejects_non_select_query() -> None:
    with pytest.raises(ValueError):
        validate_read_only_sql("DELETE FROM dataset")


def test_rejects_query_without_dataset_reference() -> None:
    with pytest.raises(ValueError):
        validate_read_only_sql("SELECT 1")


def test_rejects_dataset_name_only_inside_alias() -> None:
    with pytest.raises(ValueError):
        validate_read_only_sql("SELECT 1 AS dataset")


def test_ignores_dataset_word_inside_string_literal() -> None:
    with pytest.raises(ValueError):
        validate_read_only_sql("SELECT 'dataset' AS label")


def test_rejects_multiple_statements() -> None:
    with pytest.raises(ValueError):
        validate_read_only_sql("SELECT * FROM dataset; SELECT 1")
