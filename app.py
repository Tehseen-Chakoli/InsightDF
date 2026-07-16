from __future__ import annotations

import streamlit as st

from src.insightdf.analytics import run_analysis
from src.insightdf.config import APP_TITLE, SUPPORTED_FILE_TYPES
from src.insightdf.data_loader import load_uploaded_file
from src.insightdf.insights import build_dataset_insights
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
        st.session_state["analysis_cache"] = {}

    st.session_state.setdefault("analysis_history", [])
    st.session_state.setdefault("analysis_cache", {})


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


def _get_query_heading(entry_number: int) -> str:
    """Return a friendly heading for the latest visible query entries."""
    if entry_number == 1:
        return "Recent asked query"
    if entry_number == 2:
        return "Previous asked query"
    return f"Older asked query {entry_number - 2}"


def _render_analysis_entry(entry_number: int, question: str, result) -> None:
    """Render one question/answer block from the persisted analysis history."""
    st.markdown(f"### {_get_query_heading(entry_number)}")
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

    if result.sql_explanation:
        with st.expander("SQL explanation"):
            st.write(result.sql_explanation)

    if result.table is not None and not result.table.empty:
        st.subheader("Result table")
        st.dataframe(result.table, use_container_width=True)

    if result.figures:
        st.subheader("Visualization")
        for chart_output in result.figures:
            st.markdown(f"#### {chart_output.title}")
            st.plotly_chart(chart_output.figure, use_container_width=True)


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
    dataset_insights = build_dataset_insights(dataframe, profile)

    with st.expander("Preview dataset", expanded=True):
        left, right = st.columns([2, 1])
        with left:
            st.dataframe(dataframe.head(20), use_container_width=True)
        with right:
            st.metric("Rows", f"{profile.row_count:,}")
            st.metric("Columns", f"{profile.column_count:,}")

    with st.expander("Detected schema"):
        st.json(profile.model_dump())

    with st.expander("Automatic insights", expanded=True):
        for insight in dataset_insights:
            st.write(f"- {insight}")

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
                conversation_history = _build_conversation_history(st.session_state["analysis_history"])
                cache_key = _build_analysis_cache_key(user_question, conversation_history)
                cached_result = st.session_state["analysis_cache"].get(cache_key)

                if cached_result is None:
                    result = run_analysis(
                        dataframe=dataframe,
                        profile=profile,
                        user_question=user_question,
                        conversation_history=conversation_history,
                    )
                    st.session_state["analysis_cache"][cache_key] = result
                else:
                    result = cached_result
        except Exception as error:
            st.error(str(error))
            return

        st.session_state["analysis_history"].append(
            {
                "question": user_question.strip(),
                "result": result,
            }
        )

    history_entries = list(reversed(st.session_state["analysis_history"]))

    for index, entry in enumerate(history_entries, start=1):
        _render_analysis_entry(
            entry_number=index,
            question=entry["question"],
            result=entry["result"],
        )


def _build_conversation_history(analysis_history: list[dict]) -> list[dict[str, str]]:
    """Keep a short structured memory of recent queries for follow-up questions."""
    recent_entries = analysis_history[-3:]
    conversation_history: list[dict[str, str]] = []
    for entry in recent_entries:
        result = entry["result"]
        conversation_history.append(
            {
                "question": entry["question"],
                "answer": result.answer_text,
                "sql": result.generated_sql or "",
            }
        )
    return conversation_history


def _build_analysis_cache_key(
    user_question: str,
    conversation_history: list[dict[str, str]],
) -> str:
    """Cache repeated analyses while respecting short follow-up memory."""
    context_signature = "|".join(item["question"] for item in conversation_history)
    return f"{user_question.strip()}::{context_signature}"


if __name__ == "__main__":
    main()
