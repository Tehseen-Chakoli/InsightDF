from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()

APP_TITLE = "InsightDF"
SUPPORTED_FILE_TYPES = ["csv", "xlsx", "xls"]
DEFAULT_OPENAI_MODEL = os.getenv("INSIGHTDF_OPENAI_MODEL", "gpt-4.1-mini")
