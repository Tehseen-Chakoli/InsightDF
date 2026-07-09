from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()

APP_TITLE = "InsightDF"
SUPPORTED_FILE_TYPES = ["csv", "xlsx", "xls"]
DEFAULT_LLM_PROVIDER = os.getenv("INSIGHTDF_LLM_PROVIDER", "groq")
DEFAULT_GROQ_MODEL = os.getenv("INSIGHTDF_GROQ_MODEL", "llama-3.1-8b-instant")
