from __future__ import annotations


class InsightDFError(Exception):
    """Base exception for user-facing analytics errors."""


class MissingSchemaContextError(InsightDFError):
    """Raised when the question depends on data that is not present in the dataset."""


class QueryPlanParseError(InsightDFError):
    """Raised when the language model fails to return a valid structured query plan."""

    def __init__(self, message: str, raw_response: str) -> None:
        super().__init__(message)
        self.raw_response = raw_response
