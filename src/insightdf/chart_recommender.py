from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from pandas.api.types import is_numeric_dtype


@dataclass
class ChartRecommendation:
    chart_type: str
    facet_column: str | None
    reason: str


def recommend_chart(
    dataframe: pd.DataFrame,
    x_column: str,
    y_column: str,
    series_column: str | None,
    categorical_columns: list[str] | None,
    requested_chart_type: str | None,
) -> ChartRecommendation:
    """Choose a readable chart type and optional facet split from the query result."""
    facet_column = categorical_columns[0] if categorical_columns else None

    if requested_chart_type == "scatter" and _supports_scatter(dataframe, x_column, y_column):
        return ChartRecommendation(
            chart_type="scatter",
            facet_column=facet_column,
            reason="Both selected axes are numeric, so a scatter plot is suitable.",
        )

    if requested_chart_type == "line" and _supports_line(dataframe, x_column):
        return ChartRecommendation(
            chart_type="line",
            facet_column=facet_column,
            reason="The x-axis looks ordered or time-like, so a line chart is suitable.",
        )

    if _supports_line(dataframe, x_column):
        return ChartRecommendation(
            chart_type="line",
            facet_column=facet_column,
            reason="The result looks trend-like, so a line chart will be easier to read.",
        )

    if _supports_scatter(dataframe, x_column, y_column) and not series_column:
        return ChartRecommendation(
            chart_type="scatter",
            facet_column=facet_column,
            reason="The result compares two numeric variables, so a scatter plot is suitable.",
        )

    return ChartRecommendation(
        chart_type="bar",
        facet_column=facet_column,
        reason="A grouped bar chart is the clearest default for categorical comparisons.",
    )


def _supports_line(dataframe: pd.DataFrame, x_column: str) -> bool:
    lowered_name = x_column.casefold()
    if any(token in lowered_name for token in ("year", "date", "time", "month", "day", "week")):
        return True
    return is_numeric_dtype(dataframe[x_column])


def _supports_scatter(dataframe: pd.DataFrame, x_column: str, y_column: str) -> bool:
    return is_numeric_dtype(dataframe[x_column]) and is_numeric_dtype(dataframe[y_column])
