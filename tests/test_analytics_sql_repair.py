from __future__ import annotations

import pandas as pd

from src.insightdf.analytics import _quote_special_columns
from src.insightdf.plot_guard import prepare_plot_frame, repair_plot_sql
from src.insightdf.query_models import NumericSummary
from src.insightdf.schema import build_dataset_profile


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
        'SELECT "Year", "Entity", ["Population - Sex: all - Age: all - Variant: estimates"] AS population '
        'FROM dataset'
    )

    repaired_sql = repair_plot_sql(sql)

    assert '["Population - Sex: all - Age: all - Variant: estimates"]' not in repaired_sql
    assert '"Population - Sex: all - Age: all - Variant: estimates" AS population' in repaired_sql


def test_prepare_plot_frame_flattens_single_item_lists_for_numeric_plotting() -> None:
    result_table = pd.DataFrame(
        {
            "Year": [1950, 1951],
            "Entity": ["Afghanistan", "India"],
            "population": [[7776182], [353870058]],
        }
    )

    plot_frame = prepare_plot_frame(
        result_table=result_table,
        x_column="Year",
        y_column="population",
        series_column="Entity",
    )

    assert plot_frame.x_column == "Year"
    assert plot_frame.y_column == "population"
    assert plot_frame.series_column == "Entity"
    assert plot_frame.dataframe["population"].tolist() == [7776182, 353870058]
