from __future__ import annotations

from src.insightdf.query_models import ColumnProfile, DatasetProfile
from src.insightdf.question_guard import prepare_question_for_analysis


def test_prepare_question_preserves_generic_question_text() -> None:
    profile = DatasetProfile(
        row_count=10,
        column_count=2,
        columns=[
            ColumnProfile(name="order_id", dtype="int64", non_null_count=10, unique_count=10),
            ColumnProfile(name="status", dtype="object", non_null_count=10, unique_count=3),
        ],
    )

    result = prepare_question_for_analysis(
        profile=profile,
        dataframe=None,
        user_question="Show the average amount by status",
    )

    assert result.resolved_question == "Show the average amount by status"
    assert result.note is None
