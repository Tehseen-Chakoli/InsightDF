from __future__ import annotations

import pandas as pd

from src.insightdf.chart_recommender import recommend_chart


def test_recommend_chart_prefers_line_for_time_like_axis() -> None:
    dataframe = pd.DataFrame(
        {
            "year": [2020, 2021, 2022, 2023],
            "sales": [100, 120, 135, 150],
            "region": ["east", "east", "east", "east"],
        }
    )

    recommendation = recommend_chart(
        dataframe=dataframe,
        x_column="year",
        y_column="sales",
        series_column=None,
        categorical_columns=None,
        requested_chart_type="bar",
    )

    assert recommendation.chart_type == "line"


def test_recommend_chart_keeps_bar_for_categorical_comparison() -> None:
    dataframe = pd.DataFrame(
        {
            "region": ["east", "west", "north"],
            "order_count": [10, 14, 8],
            "channel": ["online", "retail", "online"],
        }
    )

    recommendation = recommend_chart(
        dataframe=dataframe,
        x_column="region",
        y_column="order_count",
        series_column="channel",
        categorical_columns=["channel"],
        requested_chart_type=None,
    )

    assert recommendation.chart_type == "bar"
