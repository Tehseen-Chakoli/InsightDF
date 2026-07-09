from __future__ import annotations

import re


FORBIDDEN_SQL_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bREPLACE\b",
    r"\bTRUNCATE\b",
    r"\bATTACH\b",
    r"\bCOPY\b",
    r";",
]


def validate_read_only_sql(sql: str) -> str:
    """Allow only single-statement read-only SQL."""
    normalized_sql = sql.strip()
    upper_sql = normalized_sql.upper()

    if not normalized_sql:
        raise ValueError("The generated SQL is empty.")

    if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
        raise ValueError("Only SELECT queries are allowed.")

    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, upper_sql):
            raise ValueError("The generated SQL contains a forbidden operation.")

    if "DATASET" not in upper_sql:
        raise ValueError("The generated SQL must query the uploaded dataset table.")

    return normalized_sql
