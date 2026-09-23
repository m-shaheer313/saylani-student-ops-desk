"""Environment loading and the Gemini model client.

Per constitution.md Article I, the client built here is handed to each Agent's own
definition. It is never installed as a process-wide default.
"""

import logging
import os

from agents import set_tracing_export_api_key
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL_NAME = "gemini-3.6-flash"

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

# FR-13 — the workflow every trace is filed under.
WORKFLOW_NAME = "Saylani Student Ops Desk"

# Values copied straight from .env.example still look like this.
_PLACEHOLDER_PREFIX = "your-"


def _configure_tracing() -> None:
    """Export traces under the developer's own key (Art. VII.1, plan.md §10).

    Tracing itself is always on. Only the *export* depends on a real key, so a
    missing one degrades to "spans collected, nothing shipped" with one
    explanatory line — never a crash, and never the key itself in the log
    (Art. II.5).
    """
    key = os.getenv("TRACING_EXPORT_KEY", "").strip()

    if not key or key.lower().startswith(_PLACEHOLDER_PREFIX):
        logger.warning(
            "TRACING_EXPORT_KEY is unset or still a placeholder, so traces will "
            "not be exported. Put a real OpenAI API key in .env to see runs at "
            "platform.openai.com/traces."
        )
        return

    set_tracing_export_api_key(key)


_configure_tracing()
