from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st


def load_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    """Load CSV or Excel data into a dataframe and normalize column names."""
    extension = Path(uploaded_file.name).suffix.lower()
    dataframe = _load_uploaded_file_bytes(uploaded_file.getvalue(), extension)
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
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
