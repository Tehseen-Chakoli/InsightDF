from __future__ import annotations

import pandas as pd

from src.insightdf.query_models import ColumnProfile, DatasetProfile


def build_dataset_profile(dataframe: pd.DataFrame) -> DatasetProfile:
    """Summarize the dataset so the model can reason over an arbitrary schema."""
    columns: list[ColumnProfile] = []

    for column_name in dataframe.columns:
        series = dataframe[column_name]
        sample_values = [
            str(value)
            for value in series.dropna().astype(str).head(5).tolist()
        ]
        columns.append(
            ColumnProfile(
                name=str(column_name),
                dtype=str(series.dtype),
                non_null_count=int(series.notna().sum()),
                unique_count=int(series.nunique(dropna=True)),
                sample_values=sample_values,
            )
        )

    return DatasetProfile(
        row_count=int(len(dataframe)),
        column_count=int(len(dataframe.columns)),
        columns=columns,
    )
