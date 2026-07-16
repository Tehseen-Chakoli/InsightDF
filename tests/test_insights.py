from __future__ import annotations

import pandas as pd

from src.insightdf.insights import build_dataset_insights
from src.insightdf.schema import build_dataset_profile


def test_build_dataset_insights_returns_generic_summary_points() -> None:
    dataframe = pd.DataFrame(
        {
            "region": ["east", "west", None, "east"],
            "sales": [100, 150, 175, 100],
            "status": ["open", "closed", "open", "open"],
        }
    )

    profile = build_dataset_profile(dataframe)
    insights = build_dataset_insights(dataframe, profile)

    assert any("4 rows and 3 columns" in insight for insight in insights)
    assert any("missing values" in insight for insight in insights)
    assert any("Numeric range highlights" in insight for insight in insights)
