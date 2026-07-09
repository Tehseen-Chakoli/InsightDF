from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    non_null_count: int
    unique_count: int
    sample_values: list[str] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    columns: list[ColumnProfile]


class QueryPlan(BaseModel):
    analysis_type: Literal["scalar", "table", "chart"]
    sql: str
    reasoning: str
    answer_template: str = (
        "Answer the user's question directly using the executed SQL result."
    )
    chart_type: Literal["bar", "line", "scatter"] | None = None
    x_column: str | None = None
    y_column: str | None = None
    series_column: str | None = None


class AnalysisResult(BaseModel):
    answer_text: str
    generated_sql: str | None = None


class GuardedQuestionResult(BaseModel):
    resolved_question: str
    note: str | None = None
