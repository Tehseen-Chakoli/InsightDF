from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class NumericSummary(BaseModel):
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    median_value: float | None = None
    sum_value: float | None = None


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    non_null_count: int
    unique_count: int
    sample_values: list[str] = Field(default_factory=list)
    top_values: list[str] = Field(default_factory=list)
    numeric_summary: NumericSummary | None = None


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    sample_rows: list[dict[str, object | None]] = Field(default_factory=list)


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


class SQLRepairPlan(BaseModel):
    sql: str
    reasoning: str


class AnalysisResult(BaseModel):
    answer_text: str
    generated_sql: str | None = None


class GuardedQuestionResult(BaseModel):
    resolved_question: str
    note: str | None = None
