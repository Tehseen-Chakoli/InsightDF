from __future__ import annotations

import json
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import ValidationError

from src.insightdf.config import DEFAULT_GROQ_MODEL, DEFAULT_LLM_PROVIDER
from src.insightdf.errors import QueryPlanParseError
from src.insightdf.query_models import DatasetProfile, QueryPlan, SQLRepairPlan


SYSTEM_PROMPT = """
You are a precise data analyst.
Convert the user's analytical question into a safe DuckDB SQL query over a single table named dataset.

Rules:
- Return valid JSON only.
- The SQL must be read-only and must query only the table named dataset.
- Read the full dataset profile carefully, including sample values, top values, numeric summaries, and sample rows.
- Base your reasoning only on the uploaded dataset profile.
- Do not invent unsupported columns, values, dates, identifiers, metrics, categories, or filters.
- If the user's request is incomplete or unrelated to the dataset, do not guess. Return a safe SQL query that explains the issue.
- Understand analytical intent from the wording of the question and choose the correct operation accordingly.
- Support generic analytical operations such as count, sum, total, average, mean, minimum, min, maximum, max, highest, lowest, median, percentage, ratio, grouping, comparison, sorting, and trend when the dataset supports them.
- Map user wording to SQL behavior carefully:
  - "how many", "count", "number of" -> COUNT(*)
  - "sum", "total of" -> SUM(column)
  - "average", "avg", "mean" -> AVG(column)
  - "minimum", "min", "lowest", "smallest" -> MIN(column) or ascending order with LIMIT 1 when a full row is needed
  - "maximum", "max", "highest", "largest" -> MAX(column) or descending order with LIMIT 1 when a full row is needed
- When the user asks to list, show, display, compare, or break down records, prefer table output with relevant columns.
- Prefer exact counts, sums, averages, minimums, maximums, filters, grouping, and ordering when needed.
- Use quoted identifiers for column names.
- Preserve explicit user constraints like mentioned numbers, dates, identifiers, category values, and entity names when they are supported by the dataset profile.
- Use COUNT(*) only when the user is explicitly asking how many rows, records, or groups exist.
- When the user asks for a comparison or plot, produce grouped SQL suitable for plotting.
- Only infer the closest matching column or value when the match is strongly supported by the dataset profile. Otherwise, do not guess.
- Prefer columns whose names, sample values, top values, or numeric summaries best match the user's wording.
- Use conversation history only when the current question clearly refers to earlier context such as "that", "those", "same", "compare with previous", or similar follow-up language.
- If the current question is self-contained, ignore prior conversation context.
- When the user does not include a question mark, still read the sentence normally and answer based on the same rules.
- When the question is incomplete or unrelated to the dataset, use this pattern:
  {
    "analysis_type": "scalar",
    "sql": "SELECT 'Please ask a question that uses the uploaded dataset columns and values.' AS answer",
    "reasoning": "The request is incomplete or not supported by the dataset profile.",
    "answer_template": "Return the message from the SQL result directly.",
    "chart_type": null,
    "x_column": null,
    "y_column": null,
    "series_column": null
  }
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

SQL_REPAIR_PROMPT = """
You repair DuckDB SQL queries for a single uploaded table named dataset.

Rules:
- Return valid JSON only.
- Return only read-only SQL against the table named dataset.
- Keep the repaired query as close as possible to the original analytical intent.
- Use the dataset profile, original user question, and database error message to fix the SQL.
- Do not invent unsupported columns, filters, or values.
- Preserve quoted identifiers for unusual column names.
- Output JSON in this shape:
  {
    "sql": "...",
    "reasoning": "..."
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


def generate_query_plan(
    profile: DatasetProfile,
    user_question: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> QueryPlan:
    """Ask the language model for a structured analytical plan."""
    chat_model = _build_chat_model()
    prompt = {
        # The model sees only a compact schema summary so we avoid sending the full dataset.
        "dataset_profile": profile.model_dump(),
        "user_question": user_question,
        "conversation_history": conversation_history or [],
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


def repair_sql_query(
    profile: DatasetProfile,
    user_question: str,
    failed_sql: str,
    database_error: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> SQLRepairPlan | None:
    """Ask the model to repair SQL after DuckDB reports an execution error."""
    chat_model = _build_chat_model()
    prompt = {
        "dataset_profile": profile.model_dump(),
        "user_question": user_question,
        "conversation_history": conversation_history or [],
        "failed_sql": failed_sql,
        "database_error": database_error,
    }

    messages = [
        SystemMessage(content=SQL_REPAIR_PROMPT),
        HumanMessage(content=json.dumps(prompt)),
    ]

    last_response_text = ""
    for attempt in range(2):
        response = chat_model.invoke(messages)
        last_response_text = str(response.content).strip()

        try:
            return SQLRepairPlan.model_validate_json(_extract_json_object(last_response_text))
        except (ValidationError, ValueError):
            if attempt == 0:
                messages.append(HumanMessage(content=RETRY_PROMPT))
                continue

    return None


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
