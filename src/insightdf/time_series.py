from __future__ import annotations

import re

import pandas as pd

from src.insightdf.errors import MissingSchemaContextError
from src.insightdf.query_models import DatasetProfile, QueryPlan


def build_time_series_query_plan(
    dataframe: pd.DataFrame,
    profile: DatasetProfile,
    user_question: str,
) -> QueryPlan | None:
    """Build a deterministic query plan for simple Entity-Year-measure datasets."""
    entity_column = _find_column(dataframe.columns, "Entity")
    year_column = _find_column(dataframe.columns, "Year")
    measure_column = _find_measure_column(dataframe, profile)

    if not entity_column or not year_column or not measure_column:
        return None

    normalized_question = user_question.lower()
    if "population" not in normalized_question:
        return None

    entity_value = _extract_entity_value(dataframe, entity_column, user_question)
    if not entity_value:
        return None

    year_value = _extract_year_value(user_question, dataframe[year_column])
    if not year_value:
        raise MissingSchemaContextError(
            "This dataset stores population by year. Please include a valid year from the uploaded data, "
            'for example: "What is the population of India in 2023?"'
        )

    return QueryPlan(
        analysis_type="scalar",
        sql=(
            f'SELECT "{measure_column}" AS answer '
            f'FROM dataset WHERE "{entity_column}" = \'{_escape_sql_literal(entity_value)}\' '
            f'AND "{year_column}" = {year_value}'
        ),
        reasoning=(
            "Detected an Entity-Year-measure dataset and built deterministic SQL "
            "to fetch the requested population value."
        ),
        answer_template="Return the selected population value directly.",
    )


def validate_sql_against_question(
    sql: str,
    user_question: str,
    dataframe: pd.DataFrame,
    profile: DatasetProfile,
) -> None:
    """Reject SQL that ignores obvious user constraints on common time-series datasets."""
    entity_column = _find_column(dataframe.columns, "Entity")
    year_column = _find_column(dataframe.columns, "Year")
    measure_column = _find_measure_column(dataframe, profile)
    normalized_question = user_question.lower()
    upper_sql = sql.upper()

    if "population" in normalized_question and "COUNT(" in upper_sql and "HOW MANY" not in upper_sql:
        raise ValueError(
            'The generated query counted rows instead of selecting population. '
            'Try asking a question like "What is the population of India in 2024?"'
        )

    if entity_column:
        entity_value = _extract_entity_value(dataframe, entity_column, user_question)
        if entity_value and entity_value.upper() not in upper_sql:
            raise ValueError(
                f'The generated query did not keep the requested entity "{entity_value}". '
                "Please try the question again."
            )

    if year_column:
        year_value = _extract_year_value(user_question, dataframe[year_column], raise_on_missing=False)
        if year_value and str(year_value) not in sql:
            raise ValueError(
                f"The generated query did not keep the requested year {year_value}. "
                "Please try the question again."
            )

    if measure_column and "population" in normalized_question and measure_column.upper() not in upper_sql:
        raise ValueError(
            "The generated query did not select the population column from the dataset. "
            "Please try the question again."
        )


def _find_column(columns: pd.Index, expected_name: str) -> str | None:
    for column in columns:
        if str(column).strip().lower() == expected_name.lower():
            return str(column)
    return None


def _find_measure_column(dataframe: pd.DataFrame, profile: DatasetProfile) -> str | None:
    numeric_columns = [
        column.name
        for column in profile.columns
        if pd.api.types.is_numeric_dtype(dataframe[column.name]) and column.name.lower() != "year"
    ]
    if not numeric_columns:
        return None

    preferred_columns = [
        column_name
        for column_name in numeric_columns
        if any(keyword in column_name.lower() for keyword in ("population", "estimate", "value", "count"))
    ]
    if preferred_columns:
        return preferred_columns[0]

    return numeric_columns[0]


def _extract_entity_value(dataframe: pd.DataFrame, entity_column: str, user_question: str) -> str | None:
    lowered_question = f" {user_question.lower()} "
    entity_values = sorted(
        dataframe[entity_column].dropna().astype(str).str.strip().unique().tolist(),
        key=len,
        reverse=True,
    )

    for value in entity_values:
        if f" {value.lower()} " in lowered_question:
            return value

    return None


def _extract_year_value(
    user_question: str,
    year_series: pd.Series,
    *,
    raise_on_missing: bool = True,
) -> int | None:
    year_match = re.search(r"\b(19|20)\d{2}\b", user_question)
    if not year_match:
        if raise_on_missing:
            return None
        return None

    year_value = int(year_match.group(0))
    available_years = set(year_series.dropna().astype(int).tolist())
    if year_value not in available_years:
        if raise_on_missing:
            raise MissingSchemaContextError(
                f"The year {year_value} is not present in the uploaded data. "
                "Please ask for a year that exists in the dataset."
            )
        return None

    return year_value


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")
