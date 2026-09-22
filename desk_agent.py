"""The Ops Desk agent (plan.md §2).

Module is deliberately not named `agents.py` — that would shadow the SDK package.
"""

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel

from config import MODEL_NAME, gemini_client
from student_profile import StudentProfile
from tools import get_account_status, get_assignment, get_course, list_courses

# TODO(T108/FR-4): replace with the per-turn builder composed from StudentProfile.
PLACEHOLDER_INSTRUCTIONS = (
    "You are the Saylani Student Ops Desk. Answer the student's question about their "
    "courses and account clearly and briefly. If you do not know something, say so "
    "plainly rather than guessing."
)

# Typed on StudentProfile so a missing/wrong run context is a static error,
# not a runtime path (plan.md §3).
desk_agent: Agent[StudentProfile] = Agent(
    name="Ops Desk",
    instructions=PLACEHOLDER_INSTRUCTIONS,
    tools=[list_courses, get_course, get_assignment, get_account_status],
    # Art. I.2 — the Gemini client lives in this agent's own model configuration.
    model=OpenAIChatCompletionsModel(
        model=MODEL_NAME,
        openai_client=gemini_client,
    ),
    # Art. I.5 — declared explicitly, never inherited silently.
    model_settings=ModelSettings(temperature=0.4),
)
