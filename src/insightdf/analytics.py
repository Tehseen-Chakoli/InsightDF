from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd
import plotly.express as px

from src.insightdf.llm import generate_query_plan
from src.insightdf.query_models import DatasetProfile
from src.insightdf.sql_guard import validate_read_only_sql


@dataclass
class AnalysisOutput:
    answer_text: str
    generated_sql: str | None
    table: pd.DataFrame | None
    figure: object | None


def run_analysis(
    dataframe: pd.DataFrame,
    profile: DatasetProfile,
    user_question: str,
) -> AnalysisOutput:
    """Plan the analysis, execute it against DuckDB, and format the response."""
    query_plan = generate_query_plan(profile=profile, user_question=user_question)
    safe_sql = validate_read_only_sql(query_plan.sql)

    connection = duckdb.connect(database=":memory:")
    # Register the uploaded dataframe as a virtual SQL table for deterministic computation.
    connection.register("dataset", dataframe)
    result_table = connection.execute(safe_sql).df()

    answer_text = _format_answer(result_table, query_plan.answer_template, user_question)
    figure = _build_figure(result_table, query_plan)

    return AnalysisOutput(
        answer_text=answer_text,
        generated_sql=safe_sql,
        table=result_table,
        figure=figure,
    )


def _format_answer(result_table: pd.DataFrame, answer_template: str, user_question: str) -> str:
    """Turn SQL output into a direct human-readable answer."""
    if result_table.empty:
        return f"No rows matched the question: {user_question}"

    if len(result_table) == 1 and len(result_table.columns) == 1:
        only_value = result_table.iloc[0, 0]
        return f"The exact answer is {only_value}."

    if len(result_table) == 1:
        row_as_text = ", ".join(
            f"{column}={result_table.iloc[0][column]}" for column in result_table.columns
        )
        return f"Here is the exact result: {row_as_text}."

    preview = result_table.head(10).to_dict(orient="records")
    return (
        f"I computed the result directly from the dataset. "
        f"Review the result table for the exact values. Preview: {preview}"
    )


def _build_figure(result_table: pd.DataFrame, query_plan) -> object | None:
    """Create a chart only when the model requested a visualization."""
    if query_plan.analysis_type != "chart":
        return None

    if result_table.empty or not query_plan.x_column or not query_plan.y_column:
        return None

    if query_plan.chart_type == "line":
        return px.line(
            result_table,
            x=query_plan.x_column,
            y=query_plan.y_column,
            color=query_plan.series_column,
            markers=True,
        )

    if query_plan.chart_type == "scatter":
        return px.scatter(
            result_table,
            x=query_plan.x_column,
            y=query_plan.y_column,
            color=query_plan.series_column,
        )

    return px.bar(
        result_table,
        x=query_plan.x_column,
        y=query_plan.y_column,
        color=query_plan.series_column,
        barmode="group",
    )
