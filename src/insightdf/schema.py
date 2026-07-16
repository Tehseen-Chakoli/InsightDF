from __future__ import annotations

import pandas as pd
import streamlit as st

from src.insightdf.query_models import ColumnProfile, DatasetProfile, NumericSummary


@st.cache_data(show_spinner=False)
def build_dataset_profile(dataframe: pd.DataFrame) -> DatasetProfile:
    """Summarize the dataset so the model can reason over an arbitrary schema."""
    columns: list[ColumnProfile] = []

    for column_name in dataframe.columns:
        series = dataframe[column_name]
        sample_values = [
            str(value)
            for value in series.dropna().astype(str).head(5).tolist()
        ]
        top_values = [
            str(value)
            for value in series.dropna().astype(str).value_counts().head(5).index.tolist()
        ]
        columns.append(
            ColumnProfile(
                name=str(column_name),
                dtype=str(series.dtype),
                non_null_count=int(series.notna().sum()),
                unique_count=int(series.nunique(dropna=True)),
                sample_values=sample_values,
                top_values=top_values,
                numeric_summary=_build_numeric_summary(series),
            )
        )

    sample_rows = [
        {str(column): str(value) for column, value in row.items()}
        for row in dataframe.head(3).to_dict(orient="records")
    ]

    return DatasetProfile(
        row_count=int(len(dataframe)),
        column_count=int(len(dataframe.columns)),
        columns=columns,
        sample_rows=sample_rows,
    )


def _build_numeric_summary(series: pd.Series) -> NumericSummary | None:
    if not pd.api.types.is_numeric_dtype(series):
        return None

    cleaned_series = series.dropna()
    if cleaned_series.empty:
        return NumericSummary()

    return NumericSummary(
        min_value=float(cleaned_series.min()),
        max_value=float(cleaned_series.max()),
        mean_value=float(cleaned_series.mean()),
        median_value=float(cleaned_series.median()),
        sum_value=float(cleaned_series.sum()),
    )
