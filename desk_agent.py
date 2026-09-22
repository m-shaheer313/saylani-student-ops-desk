"""The Ops Desk agent (plan.md §2).

Module is deliberately not named `agents.py` — that would shadow the SDK package.
"""

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel, RunContextWrapper

from config import MODEL_NAME, gemini_client
from student_profile import StudentProfile
from tools import (
    get_account_status,
    get_assignment,
    get_course,
    list_courses,
    lookup_course_title,
)

# spec.md §4.4 — inclusive boundary: 3 open tickets already means terse.
TERSE_THRESHOLD = 3

TONE_NORMAL = (
    "Tone: warm and helpful. A short friendly opener is fine before you answer."
)
TONE_TERSE = (
    "Tone: terse. This student already has several tickets open, so answer in as "
    "few words as the question allows. No small talk, no filler, no pleasantries "
    "— state the answer and the next step, nothing else."
)


def build_desk_instructions(
    ctx: RunContextWrapper[StudentProfile], agent: Agent[StudentProfile]
) -> str:
    """Compose the Desk's instructions fresh at the start of every run (FR-4).

    Reads the student from the run context — never from a static template
    (constitution.md Article IV.1).
    """
    profile = ctx.context

    name = (profile.name or "").strip() or "Student"
    # An unknown or unavailable course must still produce a greeting (spec.md §4.4).
    course = lookup_course_title(profile.course_id) or "your course"
    tone = TONE_TERSE if profile.open_tickets >= TERSE_THRESHOLD else TONE_NORMAL

    return (
        f"You are the Saylani Student Ops Desk. You are speaking with {name}, who is "
        f"enrolled in {course}. Open with 'Hi {name}, ' and mention their course when "
        "it is relevant to the answer.\n\n"
        "Answer questions about their courses and account. Use your tools for any "
        "course, assignment, or account fact — never guess a date, policy, or id. "
        "If a tool reports something is unavailable or not found, relay that plainly "
        "instead of inventing an answer.\n\n"
        f"{tone}"
    )

# Typed on StudentProfile so a missing/wrong run context is a static error,
# not a runtime path (plan.md §3).
desk_agent: Agent[StudentProfile] = Agent(
    name="Ops Desk",
    # FR-4 — a callable, so it is re-resolved from the context on every run.
    instructions=build_desk_instructions,
    tools=[list_courses, get_course, get_assignment, get_account_status],
    # Art. I.2 — the Gemini client lives in this agent's own model configuration.
    model=OpenAIChatCompletionsModel(
        model=MODEL_NAME,
        openai_client=gemini_client,
    ),
    # Art. I.5 — declared explicitly, never inherited silently.
    model_settings=ModelSettings(temperature=0.4),
)
