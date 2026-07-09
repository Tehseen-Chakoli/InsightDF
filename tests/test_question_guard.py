from __future__ import annotations

import pandas as pd
import pytest

from src.insightdf.errors import MissingSchemaContextError
from src.insightdf.query_models import ColumnProfile, DatasetProfile
from src.insightdf.question_guard import prepare_question_for_analysis, validate_question_against_schema


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


def test_resolves_short_trailing_token_to_dataset_value() -> None:
    profile = DatasetProfile(
        row_count=3,
        column_count=1,
        columns=[
            ColumnProfile(name="Entity", dtype="object", non_null_count=3, unique_count=3),
        ],
    )
    dataframe = pd.DataFrame({"Entity": ["India", "Indonesia", "Afghanistan"]})

    result = prepare_question_for_analysis(
        profile=profile,
        dataframe=dataframe,
        user_question="What is total population for In",
    )

    assert result.resolved_question.endswith("India")
    assert result.note is not None


def test_raises_when_value_token_is_not_present_in_dataset() -> None:
    profile = DatasetProfile(
        row_count=2,
        column_count=1,
        columns=[
            ColumnProfile(name="Entity", dtype="object", non_null_count=2, unique_count=2),
        ],
    )
    dataframe = pd.DataFrame({"Entity": ["India", "Indonesia"]})

    with pytest.raises(MissingSchemaContextError):
        prepare_question_for_analysis(
            profile=profile,
            dataframe=dataframe,
            user_question="What is total population for Atlantis",
        )
