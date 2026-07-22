from __future__ import annotations

import pandas as pd

from src.insightdf.analytics import _build_figures, _quote_special_columns
from src.insightdf.plot_guard import prepare_plot_frame, repair_plot_sql
from src.insightdf.query_models import NumericSummary, QueryPlan
from src.insightdf.schema import build_dataset_profile


def test_quotes_special_character_columns_in_generated_sql() -> None:
    columns = pd.Index(
        ["segment", "Net Sales (USD) - Adjusted"]
    )
    sql = (
        "SELECT SUM(Net Sales (USD) - Adjusted) "
        "FROM dataset WHERE segment = 'enterprise'"
    )

    repaired_sql = _quote_special_columns(sql, columns)

    assert '"Net Sales (USD) - Adjusted"' in repaired_sql


def test_dataset_profile_contains_generic_numeric_summary_and_sample_rows() -> None:
    dataframe = pd.DataFrame(
        {
            "region": ["north", "south", "north"],
            "sales": [10, 20, 30],
            "status": ["open", "closed", "open"],
        }
    )

    profile = build_dataset_profile(dataframe)

    sales_column = next(column for column in profile.columns if column.name == "sales")
    assert sales_column.numeric_summary == NumericSummary(
        min_value=10.0,
        max_value=30.0,
        mean_value=20.0,
        median_value=20.0,
        sum_value=60.0,
    )
    assert sales_column.top_values == ["10", "20", "30"]
    assert profile.sample_rows[0]["region"] == "north"


def test_plot_sql_repair_replaces_bracketed_identifier_lists() -> None:
    sql = (
        'SELECT "month", "region", ["Net Sales (USD) - Adjusted"] AS revenue '
        'FROM dataset'
    )

    repaired_sql = repair_plot_sql(sql)

    assert '["Net Sales (USD) - Adjusted"]' not in repaired_sql
    assert '"Net Sales (USD) - Adjusted" AS revenue' in repaired_sql


def test_prepare_plot_frame_flattens_single_item_lists_for_numeric_plotting() -> None:
    result_table = pd.DataFrame(
        {
            "month": ["Jan", "Feb"],
            "region": ["east", "west"],
            "revenue": [[1250], [1630]],
        }
    )

    plot_frame = prepare_plot_frame(
        result_table=result_table,
        x_column="month",
        y_column="revenue",
        series_column="region",
    )

    assert plot_frame.x_column == "month"
    assert plot_frame.y_column == "revenue"
    assert plot_frame.series_column == "region"
    assert plot_frame.dataframe["revenue"].tolist() == [1250, 1630]


def test_build_figures_adds_faceted_breakdown_for_multi_dimension_chart_results() -> None:
    result_table = pd.DataFrame(
        {
            "region": ["east", "east", "west", "west"],
            "channel": ["online", "retail", "online", "retail"],
            "quarter": [1, 1, 2, 2],
            "order_count": [15, 5, 40, 18],
        }
    )
    query_plan = QueryPlan(
        analysis_type="chart",
        sql="SELECT 1",
        reasoning="chart",
        chart_type="bar",
        x_column="region",
        y_column="order_count",
        series_column="channel",
    )

    figure_result = _build_figures(result_table, query_plan)
    chart_outputs = figure_result.outputs

    assert chart_outputs is not None
    assert len(chart_outputs) == 2
    assert "Order Count by Region and Channel" == chart_outputs[0].title
    assert "split by Quarter" in chart_outputs[1].title
    assert figure_result.note_text is not None
