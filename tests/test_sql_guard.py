from __future__ import annotations

import pytest

from src.insightdf.sql_guard import validate_read_only_sql


def test_accepts_select_query_against_dataset() -> None:
    sql = 'SELECT COUNT(*) AS total FROM dataset WHERE "Embarked" = \'C\''
    assert validate_read_only_sql(sql) == sql


def test_rejects_non_select_query() -> None:
    with pytest.raises(ValueError):
        validate_read_only_sql("DELETE FROM dataset")


def test_rejects_query_without_dataset_reference() -> None:
    with pytest.raises(ValueError):
        validate_read_only_sql("SELECT 1")
