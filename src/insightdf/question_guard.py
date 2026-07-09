from __future__ import annotations

import re

from src.insightdf.errors import MissingSchemaContextError
from src.insightdf.query_models import DatasetProfile


SEMANTIC_COLUMN_ALIASES = {
    "survived": {"survived", "survive", "survival"},
    "embarked": {"embarked", "boarded", "board", "port"},
    "sex": {"sex", "gender", "male", "female"},
    "pclass": {"pclass", "class"},
}


def validate_question_against_schema(profile: DatasetProfile, user_question: str) -> None:
    """Fail early when the question clearly depends on a missing dataset concept."""
    normalized_question = _normalize_text(user_question)
    available_columns = {_normalize_text(column.name) for column in profile.columns}

    missing_concepts: list[str] = []
    for expected_column, aliases in SEMANTIC_COLUMN_ALIASES.items():
        if _mentions_any_alias(normalized_question, aliases) and expected_column not in available_columns:
            missing_concepts.append(expected_column)

    if missing_concepts:
        formatted = ", ".join(sorted(missing_concepts))
        raise MissingSchemaContextError(
            "This dataset does not contain the required field(s): "
            f"{formatted}. Please upload a dataset that includes them or rephrase the question."
        )


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _mentions_any_alias(normalized_question: str, aliases: set[str]) -> bool:
    return any(_normalize_text(alias) in normalized_question for alias in aliases)
