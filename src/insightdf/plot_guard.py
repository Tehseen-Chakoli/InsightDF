from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd
from pandas.api.types import is_numeric_dtype


@dataclass
class PlotFrame:
    dataframe: pd.DataFrame
    x_column: str
    y_column: str
    series_column: str | None = None


def repair_plot_sql(sql: str) -> str:
    """Repair common chart-breaking SQL patterns without changing analytical intent."""

    def _replace_bracketed_identifier(match: re.Match[str]) -> str:
        identifier = next(group for group in match.groups() if group is not None)
        return f'"{identifier}"'

    # Some models emit ["column name"] instead of a scalar quoted identifier.
    repaired_sql = re.sub(
        r'\[\s*"([^"]+)"\s*\]|\[\s*\'([^\']+)\'\s*\]|\[\s*([A-Za-z_][A-Za-z0-9_ :\-/]*)\s*\]',
        _replace_bracketed_identifier,
        sql,
    )
    return repaired_sql


def prepare_plot_frame(
    result_table: pd.DataFrame,
    x_column: str | None,
    y_column: str | None,
    series_column: str | None,
) -> PlotFrame:
    """Validate and normalize chart data before it is handed to Plotly."""
    normalized_table = result_table.copy()

    for column in normalized_table.columns:
        normalized_table[column] = _flatten_single_value_sequences(normalized_table[column])
        normalized_table[column] = _coerce_series_to_numeric_if_possible(normalized_table[column])

    resolved_x = _resolve_column_name(x_column, normalized_table.columns)
    resolved_y = _resolve_column_name(y_column, normalized_table.columns)
    resolved_series = _resolve_column_name(series_column, normalized_table.columns)

    if resolved_y is None:
        resolved_y = _infer_numeric_column(normalized_table, excluded={resolved_x, resolved_series})

    if resolved_x is None:
        resolved_x = _infer_x_column(normalized_table, preferred_y=resolved_y, preferred_series=resolved_series)

    if resolved_series is None:
        resolved_series = _infer_series_column(
            normalized_table,
            excluded={resolved_x, resolved_y},
        )

    if not resolved_x or not resolved_y:
        raise ValueError(
            "I could not prepare chart-ready data from the generated SQL result. "
            "Please ask the plot question again with clearer columns or dimensions."
        )

    if not is_numeric_dtype(normalized_table[resolved_y]):
        raise ValueError(
            f"The plot metric column '{resolved_y}' is not numeric after SQL execution. "
            "Please ask for a numeric measure to plot."
        )

    return PlotFrame(
        dataframe=normalized_table,
        x_column=resolved_x,
        y_column=resolved_y,
        series_column=resolved_series,
    )


def _resolve_column_name(requested: str | None, available_columns: pd.Index) -> str | None:
    """Match model-provided plot column names to returned SQL result columns."""
    if not requested:
        return None

    cleaned_requested = requested.strip().strip('"').strip("'")
    available_lookup = {str(column): str(column) for column in available_columns}
    if cleaned_requested in available_lookup:
        return available_lookup[cleaned_requested]

    folded_lookup = {str(column).casefold(): str(column) for column in available_columns}
    return folded_lookup.get(cleaned_requested.casefold())


def _flatten_single_value_sequences(series: pd.Series) -> pd.Series:
    """Convert list-like cells such as [123] into scalar values for plotting."""

    def _flatten(value: object) -> object:
        if isinstance(value, (list, tuple)) and len(value) == 1:
            return value[0]
        return value

    return series.map(_flatten)


def _coerce_series_to_numeric_if_possible(series: pd.Series) -> pd.Series:
    """Promote fully numeric object columns into numeric dtypes."""
    if is_numeric_dtype(series):
        return series

    non_null = series.dropna()
    if non_null.empty:
        return series

    converted = pd.to_numeric(series, errors="coerce")
    if converted.notna().sum() == non_null.shape[0]:
        return converted

    return series


def _infer_numeric_column(dataframe: pd.DataFrame, excluded: set[str | None]) -> str | None:
    numeric_columns = [
        column
        for column in dataframe.columns
        if column not in excluded and is_numeric_dtype(dataframe[column])
    ]
    return numeric_columns[0] if numeric_columns else None


def _infer_x_column(
    dataframe: pd.DataFrame,
    preferred_y: str | None,
    preferred_series: str | None,
) -> str | None:
    candidates = [column for column in dataframe.columns if column not in {preferred_y, preferred_series}]

    for column in candidates:
        lowered_name = str(column).casefold()
        if any(token in lowered_name for token in ("year", "date", "time", "month", "day")):
            return str(column)

    for column in candidates:
        if not is_numeric_dtype(dataframe[column]):
            return str(column)

    return str(candidates[0]) if candidates else None


def _infer_series_column(dataframe: pd.DataFrame, excluded: set[str | None]) -> str | None:
    for column in dataframe.columns:
        if column in excluded:
            continue
        if not is_numeric_dtype(dataframe[column]) and dataframe[column].nunique(dropna=True) > 1:
            return str(column)
    return None
