from __future__ import annotations

import json
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import ValidationError

from src.insightdf.config import DEFAULT_GROQ_MODEL, DEFAULT_LLM_PROVIDER
from src.insightdf.errors import QueryPlanParseError
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

RETRY_PROMPT = (
    "Your previous response was not valid JSON for the required schema. "
    "Return only one valid JSON object with no explanation, no markdown, and no extra text."
)


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

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=json.dumps(prompt)),
    ]

    last_response_text = ""
    for attempt in range(2):
        response = chat_model.invoke(messages)
        last_response_text = str(response.content).strip()

        try:
            return QueryPlan.model_validate_json(_extract_json_object(last_response_text))
        except (ValidationError, ValueError):
            if attempt == 0:
                # Retry once with a stronger correction prompt before surfacing a user-facing error.
                messages.append(HumanMessage(content=RETRY_PROMPT))
                continue

    raise QueryPlanParseError(
        "The language model returned an invalid analysis plan. "
        "Try rephrasing the question or using a model with stronger JSON reliability.",
        raw_response=last_response_text,
    )


def _extract_json_object(response_text: str) -> str:
    """Extract the first JSON object even when the model wraps it with prose or markdown."""
    cleaned_text = (
        response_text.removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    if cleaned_text.startswith("{") and cleaned_text.endswith("}"):
        return cleaned_text

    match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
    if match:
        return match.group(0)

    raise ValueError("No JSON object found in the model response.")
