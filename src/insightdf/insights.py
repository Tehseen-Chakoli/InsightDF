from __future__ import annotations

import pandas as pd
import streamlit as st

from src.insightdf.query_models import DatasetProfile


@st.cache_data(show_spinner=False)
def build_dataset_insights(dataframe: pd.DataFrame, profile: DatasetProfile) -> list[str]:
    """Create lightweight deterministic insights for uploaded datasets."""
    insights: list[str] = [
        f"The dataset has {profile.row_count:,} rows and {profile.column_count:,} columns.",
    ]

    missing_columns = [
        column for column in profile.columns
        if column.non_null_count < profile.row_count
    ]
    if missing_columns:
        top_missing = sorted(
            missing_columns,
            key=lambda column: profile.row_count - column.non_null_count,
            reverse=True,
        )[:3]
        formatted = ", ".join(
            f"{column.name} ({profile.row_count - column.non_null_count:,} missing)"
            for column in top_missing
        )
        insights.append(f"Columns with the most missing values: {formatted}.")

    numeric_columns = [column for column in profile.columns if column.numeric_summary is not None]
    if numeric_columns:
        top_numeric = numeric_columns[:3]
        formatted = ", ".join(
            (
                f"{column.name} ranges from {column.numeric_summary.min_value:g} "
                f"to {column.numeric_summary.max_value:g}"
            )
            for column in top_numeric
            if column.numeric_summary is not None
            and column.numeric_summary.min_value is not None
            and column.numeric_summary.max_value is not None
        )
        if formatted:
            insights.append(f"Numeric range highlights: {formatted}.")

    low_cardinality_columns = [
        column for column in profile.columns
        if 1 < column.unique_count <= 12 and column.top_values
    ]
    if low_cardinality_columns:
        top_categorical = low_cardinality_columns[:2]
        formatted = "; ".join(
            f"{column.name}: {', '.join(column.top_values[:4])}"
            for column in top_categorical
        )
        insights.append(f"Useful grouping columns include {formatted}.")

    if dataframe.duplicated().any():
        duplicate_count = int(dataframe.duplicated().sum())
        insights.append(f"The uploaded data contains {duplicate_count:,} fully duplicated rows.")

    return insights
