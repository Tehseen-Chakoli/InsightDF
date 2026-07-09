from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


def load_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    """Load CSV or Excel data into a dataframe and normalize column names."""
    extension = Path(uploaded_file.name).suffix.lower()

    if extension == ".csv":
        dataframe = pd.read_csv(uploaded_file)
    elif extension in {".xlsx", ".xls"}:
        dataframe = pd.read_excel(uploaded_file)
    else:
        raise ValueError(f"Unsupported file type: {extension}")

    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    return dataframe
