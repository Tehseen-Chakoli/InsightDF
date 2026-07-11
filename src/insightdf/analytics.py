from __future__ import annotations

from dataclasses import dataclass
import re

import duckdb
import pandas as pd
import plotly.express as px

from src.insightdf.errors import QueryPlanParseError
from src.insightdf.llm import generate_query_plan
from src.insightdf.plot_guard import prepare_plot_frame, repair_plot_sql
from src.insightdf.question_guard import prepare_question_for_analysis
from src.insightdf.query_models import DatasetProfile
from src.insightdf.sql_guard import validate_read_only_sql


@dataclass
class AnalysisOutput:
    answer_text: str
    generated_sql: str | None
    table: pd.DataFrame | None
    figure: object | None
    debug_text: str | None = None
    note_text: str | None = None


def run_analysis(
    dataframe: pd.DataFrame,
    profile: DatasetProfile,
    user_question: str,
) -> AnalysisOutput:
    """Plan the analysis, execute it against DuckDB, and format the response."""
    prepared_question = prepare_question_for_analysis(
        profile=profile,
        dataframe=dataframe,
        user_question=user_question,
    )

    try:
        query_plan = generate_query_plan(
            profile=profile,
            user_question=prepared_question.resolved_question,
        )
    except QueryPlanParseError as error:
        return AnalysisOutput(
            answer_text=str(error),
            generated_sql=None,
            table=None,
            figure=None,
            debug_text=error.raw_response,
            note_text=prepared_question.note,
        )

    repaired_sql = _quote_special_columns(query_plan.sql, dataframe.columns)
    if query_plan.analysis_type == "chart":
        repaired_sql = repair_plot_sql(repaired_sql)
    safe_sql = validate_read_only_sql(repaired_sql)

    connection = duckdb.connect(database=":memory:")
    # Register the uploaded dataframe as a virtual SQL table for deterministic computation.
    connection.register("dataset", dataframe)
    try:
        result_table = connection.execute(safe_sql).df()
    except duckdb.Error as error:
        raise ValueError(
            "I could not run the generated query on this dataset. "
            "Please try a more specific question or use exact field/value names from the uploaded data."
        ) from error

    answer_text = _format_answer(result_table, query_plan.answer_template, prepared_question.resolved_question)
    figure = _build_figure(result_table, query_plan)

    return AnalysisOutput(
        answer_text=answer_text,
        generated_sql=safe_sql,
        table=result_table,
        figure=figure,
        note_text=prepared_question.note,
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

    if result_table.empty:
        return None

    plot_frame = prepare_plot_frame(
        result_table=result_table,
        x_column=query_plan.x_column,
        y_column=query_plan.y_column,
        series_column=query_plan.series_column,
    )

    if query_plan.chart_type == "line":
        return px.line(
            plot_frame.dataframe,
            x=plot_frame.x_column,
            y=plot_frame.y_column,
            color=plot_frame.series_column,
            markers=True,
        )

    if query_plan.chart_type == "scatter":
        return px.scatter(
            plot_frame.dataframe,
            x=plot_frame.x_column,
            y=plot_frame.y_column,
            color=plot_frame.series_column,
        )

    return px.bar(
        plot_frame.dataframe,
        x=plot_frame.x_column,
        y=plot_frame.y_column,
        color=plot_frame.series_column,
        barmode="group",
    )


def _quote_special_columns(sql: str, columns: pd.Index) -> str:
    """Repair generated SQL when a column name contains spaces or punctuation."""
    repaired_sql = sql

    for column in sorted((str(value) for value in columns), key=len, reverse=True):
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", column):
            continue

        repaired_sql = re.sub(
            rf'(?<!")\b{re.escape(column)}\b(?!")',
            f'"{column}"',
            repaired_sql,
        )

    return repaired_sql
