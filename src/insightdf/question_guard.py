from __future__ import annotations

import re
from difflib import get_close_matches

import pandas as pd

from src.insightdf.errors import MissingSchemaContextError
from src.insightdf.query_models import DatasetProfile, GuardedQuestionResult


SEMANTIC_COLUMN_ALIASES = {
    "survived": {"survived", "survive", "survival"},
    "embarked": {"embarked", "boarded", "board", "port"},
    "sex": {"sex", "gender", "male", "female"},
    "pclass": {"pclass", "class"},
}


def prepare_question_for_analysis(
    profile: DatasetProfile,
    dataframe: pd.DataFrame,
    user_question: str,
) -> GuardedQuestionResult:
    """Validate the question and resolve lightweight dataset-specific ambiguities."""
    validate_question_against_schema(profile=profile, user_question=user_question)

    resolved_question = user_question.strip()
    resolution_note: str | None = None

    trailing_value_match = re.search(
        r"\b(?:for|from|in)\s+([A-Za-z]{2,})\s*$",
        resolved_question,
        flags=re.IGNORECASE,
    )
    if trailing_value_match:
        token = trailing_value_match.group(1)
        resolved_value = _resolve_value_token(dataframe=dataframe, token=token)
        if resolved_value is not None and resolved_value.lower() != token.lower():
            resolved_question = re.sub(
                rf"{re.escape(token)}\s*$",
                resolved_value,
                resolved_question,
                flags=re.IGNORECASE,
            )
            resolution_note = f'Interpreted "{token}" as "{resolved_value}" based on the uploaded data.'
        elif resolved_value is None:
            raise MissingSchemaContextError(
                f'I could not find a dataset value matching "{token}". '
                "Please use a value that exists in the uploaded data."
            )

    return GuardedQuestionResult(resolved_question=resolved_question, note=resolution_note)


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


def _resolve_value_token(dataframe: pd.DataFrame, token: str) -> str | None:
    """Resolve a short trailing token to a likely categorical value from the dataset."""
    candidate_values = _collect_candidate_values(dataframe)
    lowered_map = {value.lower(): value for value in candidate_values}

    exact_match = lowered_map.get(token.lower())
    if exact_match:
        return exact_match

    prefix_matches = sorted(
        [value for value in candidate_values if value.lower().startswith(token.lower())],
        key=lambda value: (len(value), value.lower()),
    )
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    if len(prefix_matches) > 1 and len(token) <= 3:
        # Prefer the shortest prominent categorical value for very short trailing tokens like "In" -> "India".
        return prefix_matches[0]

    fuzzy_matches = get_close_matches(token.lower(), list(lowered_map.keys()), n=1, cutoff=0.8)
    if fuzzy_matches:
        return lowered_map[fuzzy_matches[0]]

    return None


def _collect_candidate_values(dataframe: pd.DataFrame) -> list[str]:
    """Search low-cardinality string columns for user-filterable categorical values."""
    candidate_values: set[str] = set()

    for column_name in dataframe.columns:
        series = dataframe[column_name]
        if not pd.api.types.is_object_dtype(series) and not pd.api.types.is_string_dtype(series):
            continue

        unique_values = series.dropna().astype(str).str.strip()
        if unique_values.nunique() > 1000:
            continue

        candidate_values.update(value for value in unique_values.unique().tolist() if value)

    return sorted(candidate_values)
