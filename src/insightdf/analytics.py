from __future__ import annotations

from dataclasses import dataclass
import re

import duckdb
import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

from src.insightdf.chart_recommender import recommend_chart
from src.insightdf.errors import QueryPlanParseError
from src.insightdf.llm import generate_query_plan, repair_sql_query
from src.insightdf.plot_guard import prepare_plot_frame, repair_plot_sql
from src.insightdf.question_guard import prepare_question_for_analysis
from src.insightdf.query_models import DatasetProfile
from src.insightdf.sql_guard import validate_read_only_sql


@dataclass
class ChartOutput:
    title: str
    figure: Figure


@dataclass
class AnalysisOutput:
    answer_text: str
    generated_sql: str | None
    table: pd.DataFrame | None
    figures: list[ChartOutput] | None
    debug_text: str | None = None
    note_text: str | None = None
    sql_explanation: str | None = None


@dataclass
class FigureBuildResult:
    outputs: list[ChartOutput] | None
    note_text: str | None = None


def run_analysis(
    dataframe: pd.DataFrame,
    profile: DatasetProfile,
    user_question: str,
    conversation_history: list[dict[str, str]] | None = None,
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
            conversation_history=conversation_history,
        )
    except QueryPlanParseError as error:
        return AnalysisOutput(
            answer_text=str(error),
            generated_sql=None,
            table=None,
            figures=None,
            debug_text=error.raw_response,
            note_text=prepared_question.note,
            sql_explanation=None,
        )

    connection = duckdb.connect(database=":memory:")
    # Register the uploaded dataframe as a virtual SQL table for deterministic computation.
    connection.register("dataset", dataframe)
    try:
        safe_sql, result_table, correction_note = _execute_query_with_correction(
            connection=connection,
            dataframe=dataframe,
            profile=profile,
            user_question=prepared_question.resolved_question,
            initial_sql=query_plan.sql,
            analysis_type=query_plan.analysis_type,
            conversation_history=conversation_history,
        )
    finally:
        connection.close()

    answer_text = _format_answer(
        result_table=result_table,
        answer_template=query_plan.answer_template,
        user_question=prepared_question.resolved_question,
    )
    figure_result = _build_figures(result_table, query_plan)

    note_text = _merge_notes(prepared_question.note, correction_note, figure_result.note_text)

    return AnalysisOutput(
        answer_text=answer_text,
        generated_sql=safe_sql,
        table=result_table,
        figures=figure_result.outputs,
        note_text=note_text,
        sql_explanation=query_plan.reasoning,
    )


def _execute_query_with_correction(
    connection: duckdb.DuckDBPyConnection,
    dataframe: pd.DataFrame,
    profile: DatasetProfile,
    user_question: str,
    initial_sql: str,
    analysis_type: str,
    conversation_history: list[dict[str, str]] | None,
) -> tuple[str, pd.DataFrame, str | None]:
    """Execute SQL and optionally repair it with the LLM if DuckDB reports an error."""
    current_sql = initial_sql
    correction_note: str | None = None
    last_error: duckdb.Error | None = None

    for attempt in range(3):
        safe_sql = _prepare_sql_for_execution(current_sql, dataframe.columns, analysis_type)
        try:
            return safe_sql, connection.execute(safe_sql).df(), correction_note
        except duckdb.Error as error:
            last_error = error
            if attempt == 2:
                break
            repair_plan = repair_sql_query(
                profile=profile,
                user_question=user_question,
                failed_sql=safe_sql,
                database_error=str(error),
                conversation_history=conversation_history,
            )
            if repair_plan is None:
                break
            current_sql = repair_plan.sql
            correction_note = (
                "The first generated SQL failed during execution, so the app automatically repaired it "
                "and retried the query."
            )

    raise ValueError(
        "I could not run the generated query on this dataset. "
        "Please try a more specific question or use exact field/value names from the uploaded data."
    ) from last_error


def _prepare_sql_for_execution(sql: str, columns: pd.Index, analysis_type: str) -> str:
    repaired_sql = _quote_special_columns(sql, columns)
    if analysis_type == "chart":
        repaired_sql = repair_plot_sql(repaired_sql)
    return validate_read_only_sql(repaired_sql)


def _format_answer(result_table: pd.DataFrame, answer_template: str, user_question: str) -> str:
    """Turn SQL output into a direct human-readable answer."""
    if result_table.empty:
        return f"No rows matched the question: {user_question}"

    if len(result_table) == 1 and len(result_table.columns) == 1:
        only_value = result_table.iloc[0, 0]
        if _should_return_scalar_message(answer_template):
            return str(only_value)
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


def _build_figures(result_table: pd.DataFrame, query_plan) -> FigureBuildResult:
    """Create chart outputs that stay readable when multiple dimensions are returned."""
    if query_plan.analysis_type != "chart":
        return FigureBuildResult(outputs=None, note_text=None)

    if result_table.empty:
        return FigureBuildResult(outputs=None, note_text=None)

    plot_frame = prepare_plot_frame(
        result_table=result_table,
        x_column=query_plan.x_column,
        y_column=query_plan.y_column,
        series_column=query_plan.series_column,
    )
    recommendation = recommend_chart(
        dataframe=plot_frame.dataframe,
        x_column=plot_frame.x_column,
        y_column=plot_frame.y_column,
        series_column=plot_frame.series_column,
        categorical_columns=plot_frame.categorical_columns,
        requested_chart_type=query_plan.chart_type,
    )

    chart_outputs: list[ChartOutput] = []
    primary_title = _build_chart_title(plot_frame)
    primary_figure = _build_primary_figure(plot_frame, recommendation.chart_type, primary_title)
    chart_outputs.append(ChartOutput(title=primary_title, figure=primary_figure))

    if recommendation.facet_column:
        breakdown_title = (
            f"{_humanize_label(plot_frame.y_column)} by {_humanize_label(plot_frame.x_column)} "
            f"split by {_humanize_label(recommendation.facet_column)}"
        )
        breakdown_figure = _build_faceted_bar_figure(
            plot_frame=plot_frame,
            facet_column=recommendation.facet_column,
            title=breakdown_title,
        )
        chart_outputs.append(ChartOutput(title=breakdown_title, figure=breakdown_figure))

    return FigureBuildResult(
        outputs=chart_outputs,
        note_text=f"Chart recommendation: {recommendation.reason}",
    )


def _build_primary_figure(plot_frame, chart_type: str, title: str) -> Figure:
    """Create the main chart using consistent labels and a stronger color palette."""
    labels = _build_plot_labels(plot_frame)
    color_sequence = px.colors.qualitative.Bold

    if chart_type == "line":
        figure = px.line(
            plot_frame.dataframe,
            x=plot_frame.x_column,
            y=plot_frame.y_column,
            color=plot_frame.series_column,
            markers=True,
            title=title,
            labels=labels,
            color_discrete_sequence=color_sequence,
        )
    elif chart_type == "scatter":
        figure = px.scatter(
            plot_frame.dataframe,
            x=plot_frame.x_column,
            y=plot_frame.y_column,
            color=plot_frame.series_column,
            title=title,
            labels=labels,
            color_discrete_sequence=color_sequence,
        )
    else:
        figure = px.bar(
            plot_frame.dataframe,
            x=plot_frame.x_column,
            y=plot_frame.y_column,
            color=plot_frame.series_column,
            barmode="group",
            title=title,
            labels=labels,
            color_discrete_sequence=color_sequence,
        )

    return _style_figure(figure)


def _build_faceted_bar_figure(plot_frame, facet_column: str, title: str) -> Figure:
    """Create a clearer small-multiples comparison when extra categorical dimensions exist."""
    figure = px.bar(
        plot_frame.dataframe,
        x=plot_frame.x_column,
        y=plot_frame.y_column,
        color=plot_frame.series_column,
        facet_col=facet_column,
        barmode="group",
        title=title,
        labels=_build_plot_labels(plot_frame),
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    figure.for_each_annotation(
        lambda annotation: annotation.update(
            text=annotation.text.split("=")[-1].strip()
        )
    )
    return _style_figure(figure)


def _build_chart_title(plot_frame) -> str:
    if plot_frame.series_column:
        return (
            f"{_humanize_label(plot_frame.y_column)} by {_humanize_label(plot_frame.x_column)} "
            f"and {_humanize_label(plot_frame.series_column)}"
        )
    return f"{_humanize_label(plot_frame.y_column)} by {_humanize_label(plot_frame.x_column)}"


def _build_plot_labels(plot_frame) -> dict[str, str]:
    labels = {
        plot_frame.x_column: _humanize_label(plot_frame.x_column),
        plot_frame.y_column: _humanize_label(plot_frame.y_column),
    }
    if plot_frame.series_column:
        labels[plot_frame.series_column] = _humanize_label(plot_frame.series_column)
    if plot_frame.categorical_columns:
        for column in plot_frame.categorical_columns:
            labels[column] = _humanize_label(column)
    return labels


def _humanize_label(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _style_figure(figure: Figure) -> Figure:
    figure.update_layout(
        legend_title_text=figure.layout.legend.title.text if figure.layout.legend else None,
        template="plotly_white",
        title_x=0.02,
        title_font_size=20,
        font=dict(size=14),
        margin=dict(l=40, r=20, t=70, b=40),
    )
    figure.update_xaxes(showgrid=False, title_font=dict(size=15))
    figure.update_yaxes(showgrid=True, gridcolor="#d9dde7", title_font=dict(size=15))
    return figure


def _merge_notes(*notes: str | None) -> str | None:
    merged_notes = [note for note in notes if note]
    if not merged_notes:
        return None
    return " ".join(merged_notes)


def _should_return_scalar_message(answer_template: str) -> bool:
    normalized_template = answer_template.strip().casefold()
    return "return the message from the sql result directly" in normalized_template


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
