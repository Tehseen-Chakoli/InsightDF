from __future__ import annotations

import pytest

from src.insightdf.errors import MissingSchemaContextError
from src.insightdf.query_models import ColumnProfile, DatasetProfile
from src.insightdf.question_guard import validate_question_against_schema


def test_blocks_question_when_survived_column_is_missing() -> None:
    profile = DatasetProfile(
        row_count=10,
        column_count=2,
        columns=[
            ColumnProfile(name="PassengerId", dtype="int64", non_null_count=10, unique_count=10),
            ColumnProfile(name="Embarked", dtype="object", non_null_count=10, unique_count=3),
        ],
    )

    with pytest.raises(MissingSchemaContextError):
        validate_question_against_schema(profile, "How many people survived who boarded from C?")


def test_allows_question_when_required_columns_exist() -> None:
    profile = DatasetProfile(
        row_count=10,
        column_count=2,
        columns=[
            ColumnProfile(name="Survived", dtype="int64", non_null_count=10, unique_count=2),
            ColumnProfile(name="Embarked", dtype="object", non_null_count=10, unique_count=3),
        ],
    )

    validate_question_against_schema(profile, "How many people survived who boarded from C?")
