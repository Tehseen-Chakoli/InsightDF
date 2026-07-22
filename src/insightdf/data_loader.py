from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st


def load_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    """Load CSV or Excel data into a dataframe and normalize column names."""
    extension = Path(uploaded_file.name).suffix.lower()
    dataframe = _load_uploaded_file_bytes(uploaded_file.getvalue(), extension)
    dataframe.columns = _normalize_column_names(dataframe.columns)
    return dataframe


@st.cache_data(show_spinner=False)
def _load_uploaded_file_bytes(file_bytes: bytes, extension: str) -> pd.DataFrame:
    """Cache parsed tabular data so repeated reruns do not reload large files from scratch."""
    if extension == ".csv":
        return pd.read_csv(BytesIO(file_bytes))
    elif extension in {".xlsx", ".xls"}:
        return pd.read_excel(BytesIO(file_bytes))
    else:
        raise ValueError(f"Unsupported file type: {extension}")


def _normalize_column_names(columns) -> list[str]:
    """Create stable, non-empty, unique column names across arbitrary uploads."""
    normalized_columns: list[str] = []
    counts: dict[str, int] = {}

    for index, raw_column in enumerate(columns, start=1):
        cleaned_name = str(raw_column).strip()
        if not cleaned_name or cleaned_name.lower() == "nan":
            cleaned_name = f"column_{index}"

        counts[cleaned_name] = counts.get(cleaned_name, 0) + 1
        if counts[cleaned_name] > 1:
            cleaned_name = f"{cleaned_name}__{counts[cleaned_name]}"

        normalized_columns.append(cleaned_name)

    return normalized_columns
