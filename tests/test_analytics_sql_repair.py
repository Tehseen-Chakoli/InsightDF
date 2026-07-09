from __future__ import annotations

import pandas as pd

from src.insightdf.analytics import _quote_special_columns


def test_quotes_special_character_columns_in_generated_sql() -> None:
    columns = pd.Index(
        ["Entity", "Population - Sex: all - Age: all - Variant: estimates"]
    )
    sql = (
        "SELECT SUM(Population - Sex: all - Age: all - Variant: estimates) "
        "FROM dataset WHERE Entity = 'India'"
    )

    repaired_sql = _quote_special_columns(sql, columns)

    assert '"Population - Sex: all - Age: all - Variant: estimates"' in repaired_sql
