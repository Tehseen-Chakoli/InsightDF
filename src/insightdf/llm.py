from __future__ import annotations

import json
import os

from openai import OpenAI

from src.insightdf.config import DEFAULT_OPENAI_MODEL
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


def generate_query_plan(profile: DatasetProfile, user_question: str) -> QueryPlan:
    """Ask the language model for a structured analytical plan."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add your API key before using natural-language analysis."
        )

    client = OpenAI(api_key=api_key)
    prompt = {
        # The model sees only a compact schema summary so we avoid sending the full dataset.
        "dataset_profile": profile.model_dump(),
        "user_question": user_question,
    }

    response = client.responses.create(
        model=DEFAULT_OPENAI_MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(prompt)},
        ],
    )

    response_text = response.output_text.strip()
    response_text = response_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return QueryPlan.model_validate_json(response_text)
