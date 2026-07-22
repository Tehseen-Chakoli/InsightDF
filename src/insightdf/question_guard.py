from __future__ import annotations

import re

from src.insightdf.errors import MissingSchemaContextError
from src.insightdf.query_models import DatasetProfile, GuardedQuestionResult


def prepare_question_for_analysis(
    profile: DatasetProfile,
    dataframe,
    user_question: str,
) -> GuardedQuestionResult:
    """Normalize the incoming question without imposing dataset-specific assumptions."""
    _ = dataframe

    if profile.column_count == 0:
        raise MissingSchemaContextError("The uploaded dataset has no columns to analyze.")

    if profile.row_count == 0:
        raise MissingSchemaContextError("The uploaded dataset is empty, so there is nothing to analyze yet.")

    normalized_question = re.sub(r"\s+", " ", user_question).strip()
    if not normalized_question:
        raise MissingSchemaContextError("Enter a question about the uploaded dataset before running the analysis.")

    return GuardedQuestionResult(resolved_question=normalized_question, note=None)
