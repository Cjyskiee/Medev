"""Settings read once from the .env file when the app starts."""

import os
from pathlib import Path

from dotenv import load_dotenv

# The .env file sits in the project root, one level above app/.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@localhost:5432/medev")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

SCORE_MIN = float(os.getenv("SCORE_MIN", "0.30"))
TOP_K = int(os.getenv("TOP_K", "5"))

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "medev-f910b")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "")
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").strip().lower() in {"1", "true", "yes", "on"}
