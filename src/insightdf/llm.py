from __future__ import annotations

import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.insightdf.config import DEFAULT_GROQ_MODEL, DEFAULT_LLM_PROVIDER
from src.insightdf.query_models import DatasetProfile, QueryPlan


SYSTEM_PROMPT = """
You are a precise data analyst.
Convert the user's analytical question into a safe DuckDB SQL query over a single table named dataset.

Rules:
- Return valid JSON only.
- The SQL must be read-only and must query only the table named dataset.
- Prefer exact counts, sums, averages, minimums, maximums, filters, grouping, and ordering when needed.
- Use quoted identifiers for column names.
- When the user asks for a comparison or plot, produce grouped SQL suitable for plotting.
- If a dataset does not contain the exact words used by the user, infer the closest matching columns and values from the schema.
- The output JSON must match this shape:
  {
    "analysis_type": "scalar" | "table" | "chart",
    "sql": "...",
    "reasoning": "...",
    "answer_template": "...",
    "chart_type": "bar" | "line" | "scatter" | null,
    "x_column": "..." | null,
    "y_column": "..." | null,
    "series_column": "..." | null
  }
""".strip()


def _build_chat_model():
    """Create the configured chat model behind a provider-agnostic interface."""
    provider = DEFAULT_LLM_PROVIDER.lower().strip()

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your local .env file before using the app."
            )
        return ChatGroq(model=DEFAULT_GROQ_MODEL, api_key=api_key, temperature=0)

    raise RuntimeError(
        f"Unsupported LLM provider: {DEFAULT_LLM_PROVIDER}. "
        "Add a new provider in src/insightdf/llm.py to switch models later."
    )


def generate_query_plan(profile: DatasetProfile, user_question: str) -> QueryPlan:
    """Ask the language model for a structured analytical plan."""
    chat_model = _build_chat_model()
    prompt = {
        # The model sees only a compact schema summary so we avoid sending the full dataset.
        "dataset_profile": profile.model_dump(),
        "user_question": user_question,
    }

    response = chat_model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(prompt)),
        ]
    )

    response_text = str(response.content).strip()
    response_text = (
        response_text.removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    return QueryPlan.model_validate_json(response_text)
