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
]


def validate_read_only_sql(sql: str) -> str:
    """Allow only single-statement read-only SQL."""
    normalized_sql = sql.strip()

    # Many models end safe SELECT queries with a single trailing semicolon.
    if normalized_sql.endswith(";"):
        normalized_sql = normalized_sql[:-1].rstrip()

    upper_sql = normalized_sql.upper()

    if not normalized_sql:
        raise ValueError("The generated SQL is empty.")

    sql_without_comments = _strip_sql_comments(normalized_sql)
    sql_for_validation = _strip_sql_string_literals(sql_without_comments)
    upper_sql = sql_for_validation.upper()

    if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
        raise ValueError("Only SELECT queries are allowed.")

    if ";" in sql_for_validation:
        raise ValueError("The generated SQL contains multiple statements.")

    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, upper_sql):
            raise ValueError("The generated SQL contains a forbidden operation.")

    if not _references_dataset_table(sql_for_validation):
        raise ValueError("The generated SQL must query the uploaded dataset table.")

    return normalized_sql


def _strip_sql_comments(sql: str) -> str:
    """Remove SQL comments so validation checks inspect only executable code."""
    without_block_comments = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--.*?(?=\n|$)", " ", without_block_comments)


def _strip_sql_string_literals(sql: str) -> str:
    """Remove quoted string contents to avoid false matches in safety checks."""
    return re.sub(r"'(?:''|[^'])*'", "''", sql)


def _references_dataset_table(sql: str) -> bool:
    """Require an actual FROM or JOIN reference to the uploaded dataset table."""
    return re.search(r'\b(?:FROM|JOIN)\s+"?dataset"?\b', sql, flags=re.IGNORECASE) is not None
