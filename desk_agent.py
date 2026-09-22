"""The Ops Desk agent (plan.md §2).

Module is deliberately not named `agents.py` — that would shadow the SDK package.
"""

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel

from config import MODEL_NAME, gemini_client

# TODO(T108/FR-4): replace with the per-turn builder composed from StudentProfile.
PLACEHOLDER_INSTRUCTIONS = (
    "You are the Saylani Student Ops Desk. Answer the student's question about their "
    "courses and account clearly and briefly. If you do not know something, say so "
    "plainly rather than guessing."
)

desk_agent = Agent(
    name="Ops Desk",
    instructions=PLACEHOLDER_INSTRUCTIONS,
    # Art. I.2 — the Gemini client lives in this agent's own model configuration.
    model=OpenAIChatCompletionsModel(
        model=MODEL_NAME,
        openai_client=gemini_client,
    ),
    # Art. I.5 — declared explicitly, never inherited silently.
    model_settings=ModelSettings(temperature=0.4),
)
