from __future__ import annotations

import pandas as pd

from src.insightdf.analytics import _quote_special_columns
from src.insightdf.query_models import ColumnProfile, DatasetProfile
from src.insightdf.time_series import build_time_series_query_plan, validate_sql_against_question


def test_quotes_special_character_columns_in_generated_sql() -> None:
    columns = pd.Index(
        ["Entity", "Population - Sex: all - Age: all - Variant: estimates"]
    )
    sql = (
        "SELECT SUM(Population - Sex: all - Age: all - Variant: estimates) "
        "FROM dataset WHERE Entity = 'India'"
    )

    repaired_sql = _quote_special_columns(sql, columns)

    assert '"Population - Sex: all - Age: all - Variant: estimates"' in repaired_sql


def test_builds_deterministic_population_query_for_entity_year_dataset() -> None:
    dataframe = pd.DataFrame(
        {
            "Entity": ["India", "India", "Afghanistan"],
            "Year": [2023, 2024, 2024],
            "Population - Sex: all - Age: all - Variant: estimates": [100, 110, 20],
            "Code": ["IND", "IND", "AFG"],
        }
    )
    profile = DatasetProfile(
        row_count=3,
        column_count=4,
        columns=[
            ColumnProfile(name="Entity", dtype="object", non_null_count=3, unique_count=2),
            ColumnProfile(name="Year", dtype="int64", non_null_count=3, unique_count=2),
            ColumnProfile(
                name="Population - Sex: all - Age: all - Variant: estimates",
                dtype="int64",
                non_null_count=3,
                unique_count=3,
            ),
            ColumnProfile(name="Code", dtype="object", non_null_count=3, unique_count=2),
        ],
    )

    plan = build_time_series_query_plan(
        dataframe=dataframe,
        profile=profile,
        user_question="What is the population of India in 2024?",
    )

    assert plan is not None
    assert '"Entity" = \'India\'' in plan.sql
    assert '"Year" = 2024' in plan.sql
    assert "COUNT(" not in plan.sql.upper()


def test_rejects_sql_that_changes_requested_entity_or_year() -> None:
    dataframe = pd.DataFrame(
        {
            "Entity": ["India", "Afghanistan"],
            "Year": [2024, 1954],
            "Population - Sex: all - Age: all - Variant: estimates": [110, 20],
        }
    )
    profile = DatasetProfile(
        row_count=2,
        column_count=3,
        columns=[
            ColumnProfile(name="Entity", dtype="object", non_null_count=2, unique_count=2),
            ColumnProfile(name="Year", dtype="int64", non_null_count=2, unique_count=2),
            ColumnProfile(
                name="Population - Sex: all - Age: all - Variant: estimates",
                dtype="int64",
                non_null_count=2,
                unique_count=2,
            ),
        ],
    )

    try:
        validate_sql_against_question(
            sql='SELECT COUNT(*) AS answer FROM dataset WHERE "Year" = 1954 AND "Entity" = \'Afghanistan\'',
            user_question="What is the population of India in 2024?",
            dataframe=dataframe,
            profile=profile,
        )
    except ValueError as error:
        assert "population" in str(error).lower() or "entity" in str(error).lower()
    else:
        raise AssertionError("Expected the SQL faithfulness validator to reject the query.")
