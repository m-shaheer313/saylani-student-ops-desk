"""The on-topic input guardrail (FR-8, plan.md §5).

A small, cheap agent classifies the incoming message before the Desk's own model is
invoked. Off-topic messages trip the wire, so a rejected turn never bills the Desk's
primary model (constitution.md Article VI.3).
"""

import logging

from agents import (
    Agent,
    GuardrailFunctionOutput,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunContextWrapper,
    Runner,
    input_guardrail,
)
from pydantic import BaseModel

from config import MODEL_NAME, gemini_client
from student_profile import StudentProfile

logger = logging.getLogger(__name__)

# The guardrail is one classification turn; it never needs tools or a handoff.
GUARDRAIL_MAX_TURNS = 2

REFUSAL_MESSAGE = (
    "Sorry — I can only help with Saylani bootcamp matters: your courses, "
    "assignments and deadlines, careers after the programme, and account or "
    "enrolment questions. Ask me something along those lines and I'll help."
)

# Shown when the check itself could not run (spec.md §4.8 edge case). Fails toward
# asking the student to rephrase, never toward letting an unchecked message pass.
CHECK_FAILED_MESSAGE = (
    "Sorry — I couldn't check that message just now. Could you rephrase it, "
    "mentioning the course, assignment, or account matter it relates to?"
)


class TopicCheck(BaseModel):
    on_topic: bool
    reason: str


GUARDRAIL_INSTRUCTIONS = (
    "You screen messages arriving at the Saylani student help desk. Decide only "
    "whether a message belongs here at all. You never answer it.\n\n"
    "In scope: the bootcamp's courses, class schedules, assignments and deadlines, "
    "submission and attendance policy, enrolment, fees, accounts and tickets, and "
    "careers after the programme.\n\n"
    "Apply these rules exactly:\n"
    "1. Greetings, thanks, and closers — 'hi', 'thanks', 'that's all', 'bye' — are "
    "ALWAYS on_topic. They are ordinary framing around a conversation, not the "
    "substance of a request. Never reject them.\n"
    "2. A broad question that is plausibly about the student's learning or career "
    "is on_topic, even with no course named. 'What programming language should I "
    "learn?' is on_topic. When a question could reasonably be career or study "
    "advice, treat it as on_topic.\n"
    "3. Judge a mixed message by its PRIMARY intent. 'What's my assignment due "
    "date, and also what's the weather?' is primarily about an assignment, so it "
    "is on_topic. The desk will decline the unrelated part itself.\n"
    "4. Reject — on_topic=false — only when a message has no discernible "
    "bootcamp-related intent at all: sports scores, celebrity news, recipes, "
    "unrelated general trivia, requests to write code for someone else's "
    "unrelated project.\n\n"
    "When genuinely torn, pass the message through. A wrongly rejected student is "
    "a worse outcome than a wrongly accepted question.\n\n"
    "Give a short reason for the decision."
)

topic_guard_agent: Agent[StudentProfile] = Agent(
    name="Topic Guardrail",
    instructions=GUARDRAIL_INSTRUCTIONS,
    tools=[],
    model=OpenAIChatCompletionsModel(
        model=MODEL_NAME,
        openai_client=gemini_client,
    ),
    # Near-deterministic: the same message should classify the same way (Art. I.5).
    model_settings=ModelSettings(temperature=0.0),
    output_type=TopicCheck,
)


class GuardrailCheckFailed(Exception):
    """The guardrail could not reach a verdict (spec.md §4.8 edge case)."""


@input_guardrail(
    name="on_topic",
    # Sequential, not parallel: the Desk's model must never be invoked for a
    # rejected turn (spec.md §4.8 acceptance criterion, Art. VI.3).
    run_in_parallel=False,
)
async def on_topic_guardrail(
    ctx: RunContextWrapper[StudentProfile],
    agent: Agent[StudentProfile],
    user_input: str | list,
) -> GuardrailFunctionOutput:
    """Trip the wire when a message has no bootcamp-related intent."""
    try:
        result = await Runner.run(
            topic_guard_agent,
            user_input,
            context=ctx.context,
            max_turns=GUARDRAIL_MAX_TURNS,
        )
        check = result.final_output
    except Exception as exc:
        # Art. VIII.2 / spec.md §4.8 — surface this as its own condition at the
        # run boundary rather than passing an unchecked message to the Desk.
        logger.error("Guardrail check failed to run: %s", exc)
        raise GuardrailCheckFailed(str(exc)) from exc

    if not isinstance(check, TopicCheck):
        logger.error("Guardrail returned %s, not a TopicCheck", type(check).__name__)
        raise GuardrailCheckFailed(f"unexpected guardrail output: {type(check)}")

    return GuardrailFunctionOutput(
        output_info=check,
        tripwire_triggered=not check.on_topic,
    )
