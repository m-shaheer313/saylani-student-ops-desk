"""Environment loading and the Gemini model client.

Per constitution.md Article I, the client built here is handed to each Agent's own
definition. It is never installed as a process-wide default.
"""

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import set_tracing_disabled
set_tracing_disabled(True)

load_dotenv()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL_NAME = "gemini-2.5-flash"

# plan.md §8 — bounds the worst case of a malfunctioning loop to 10 model calls.
MAX_TURNS = 10


def _require(name: str) -> str:
    """Return an env var's value, or exit with one readable line (Art. II.4)."""
    value = os.getenv(name, "").strip()
    if not value:
        # SystemExit prints only this message and exits 1 — no traceback.
        raise SystemExit(
            f"Missing required environment variable: {name}. "
            "Copy .env.example to .env and fill it in."
        )
    return value


GEMINI_API_KEY = _require("GEMINI_API_KEY")

gemini_client = AsyncOpenAI(
    api_key=GEMINI_API_KEY,
    base_url=GEMINI_BASE_URL,
)
