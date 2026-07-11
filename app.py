from __future__ import annotations

import streamlit as st

from src.insightdf.analytics import run_analysis
from src.insightdf.config import APP_TITLE, SUPPORTED_FILE_TYPES
from src.insightdf.data_loader import load_uploaded_file
from src.insightdf.schema import build_dataset_profile


st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide")


def _get_dataset_key(uploaded_file) -> str:
    """Build a stable key so chat history resets only when the uploaded file changes."""
    return f"{uploaded_file.name}:{uploaded_file.size}"


def _initialize_session_state(dataset_key: str) -> None:
    """Prepare per-dataset chat history storage in Streamlit session state."""
    current_dataset_key = st.session_state.get("dataset_key")
    if current_dataset_key != dataset_key:
        st.session_state["dataset_key"] = dataset_key
        st.session_state["analysis_history"] = []

    st.session_state.setdefault("analysis_history", [])


def _inject_button_styles() -> None:
    """Give the primary action a clearer violet visual treatment."""
    st.markdown(
        """
        <style>
        div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #6d28d9, #8b5cf6);
            border: 1px solid #6d28d9;
            color: #ffffff;
            font-weight: 600;
        }

        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #5b21b6, #7c3aed);
            border-color: #5b21b6;
            color: #ffffff;
        }

        div[data-testid="stTextArea"] textarea:focus {
            border-color: #7c3aed !important;
            box-shadow: 0 0 0 1px #7c3aed !important;
        }

        div[data-testid="stTextArea"] textarea:focus-visible {
            outline: none !important;
            border-color: #7c3aed !important;
            box-shadow: 0 0 0 1px #7c3aed !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_analysis_entry(entry_number: int, question: str, result) -> None:
    """Render one question/answer block from the persisted analysis history."""
    st.markdown(f"### Query {entry_number}")
    st.write(f"**Question:** {question}")

    st.subheader("Answer")
    st.write(result.answer_text)

    if result.note_text:
        st.info(result.note_text)

    if result.debug_text:
        with st.expander("Model debug output"):
            st.code(result.debug_text)

    if result.generated_sql:
        with st.expander("Generated SQL"):
            st.code(result.generated_sql, language="sql")

    if result.table is not None and not result.table.empty:
        st.subheader("Result table")
        st.dataframe(result.table, use_container_width=True)

    if result.figure is not None:
        st.subheader("Visualization")
        st.plotly_chart(result.figure, use_container_width=True)


def main() -> None:
    """Render the Streamlit application."""
    _inject_button_styles()
    st.title(APP_TITLE)
    st.caption(
        "Upload any CSV or Excel dataset, ask analytical questions in natural language, "
        "and get exact answers backed by the uploaded data."
    )

    uploaded_file = st.file_uploader(
        "Upload a dataset",
        type=SUPPORTED_FILE_TYPES,
        help="Supported formats: CSV, XLSX, XLS.",
    )

    if uploaded_file is None:
        st.info("Upload a dataset to begin asking questions.")
        return

    _initialize_session_state(_get_dataset_key(uploaded_file))

    dataframe = load_uploaded_file(uploaded_file)
    profile = build_dataset_profile(dataframe)

    with st.expander("Preview dataset", expanded=True):
        left, right = st.columns([2, 1])
        with left:
            st.dataframe(dataframe.head(20), use_container_width=True)
        with right:
            st.metric("Rows", f"{profile.row_count:,}")
            st.metric("Columns", f"{profile.column_count:,}")

    with st.expander("Detected schema"):
        st.json(profile.model_dump())

    user_question = st.text_area(
        "Ask your query",
        placeholder="Example: What is the average sales amount for each region?",
        height=120,
    )

    if st.button("Analyze", type="primary", use_container_width=True):
        if not user_question.strip():
            st.warning("Enter a question before running the analysis.")
            return

        try:
            # Keep the app flow thin here and delegate the heavy lifting to the analytics layer.
            with st.spinner("Understanding the dataset and running the analysis..."):
                result = run_analysis(
                    dataframe=dataframe,
                    profile=profile,
                    user_question=user_question,
                )
        except Exception as error:
            st.error(str(error))
            return

        st.session_state["analysis_history"].append(
            {
                "question": user_question.strip(),
                "result": result,
            }
        )

    for index, entry in enumerate(st.session_state["analysis_history"], start=1):
        _render_analysis_entry(
            entry_number=index,
            question=entry["question"],
            result=entry["result"],
        )


if __name__ == "__main__":
    main()
