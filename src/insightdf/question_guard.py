from __future__ import annotations

from src.insightdf.query_models import DatasetProfile, GuardedQuestionResult


def prepare_question_for_analysis(
    profile: DatasetProfile,
    dataframe,
    user_question: str,
) -> GuardedQuestionResult:
    """Normalize the incoming question without imposing dataset-specific assumptions."""
    _ = profile, dataframe
    return GuardedQuestionResult(resolved_question=user_question.strip(), note=None)
