"""The Summariser, exposed to the Desk as a tool (FR-6, plan.md §2/§3).

A handoff transfers authorship of the reply; a tool call does not. The Summariser
must never speak to the student in its own voice, so it is wired as a tool only and
never appears in any agent's `handoffs`.
"""

import json
import logging

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel, function_tool
from agents.tool_context import ToolContext

from config import MODEL_NAME, gemini_client
from student_profile import StudentProfile

logger = logging.getLogger(__name__)

EMPTY_INPUT_RESULT = "Nothing to summarize."

SUMMARISER_INSTRUCTIONS = (
    "You compress text. That is your only job.\n\n"
    "Return at most three lines. Never add a fact, number, date, caveat, or "
    "conclusion that is not present in the input — you have no knowledge to add, "
    "only text to shorten.\n\n"
    "If the input is already three lines or shorter, do not pad it, do not restate "
    "it at greater length, and do not restructure it into a list or a heading. "
    "Return it as it is, unchanged in meaning, at most three lines.\n\n"
    "Output the summary text alone: no preamble, no 'Summary:' label, no closing "
    "remark."
)

summariser: Agent[StudentProfile] = Agent(
    name="Summariser",
    instructions=SUMMARISER_INSTRUCTIONS,
    tools=[],
    model=OpenAIChatCompletionsModel(
        model=MODEL_NAME,
        openai_client=gemini_client,
    ),
    # Low temperature: compression should not paraphrase creatively (plan.md §2).
    model_settings=ModelSettings(temperature=0.1),
)

_summarise_via_model = summariser.as_tool(
    tool_name="summarise_policy_model",
    tool_description="Internal: run the Summariser agent over some text.",
    # None => raise instead of returning the provider's raw error text as a
    # "summary". The wrapper below turns it into a controlled message, so the
    # model never sees an API error string (Art. III.3).
    failure_error_function=None,
)


@function_tool(
    name_override="summarise_policy",
    description_override=(
        "Condense long policy or schedule text to at most three lines. Pass the text "
        "you want shortened; you then relay the result to the student in your own "
        "voice."
    ),
)
async def summarise_policy(ctx: ToolContext[StudentProfile], text: str) -> str:
    """Summarise `text` to three lines or fewer."""
    # Edge case (spec.md §4.6): nothing to send, so no billed model call.
    if not text or not text.strip():
        return EMPTY_INPUT_RESULT

    try:
        result = await _summarise_via_model.on_invoke_tool(
            ctx, json.dumps({"input": text})
        )
    except Exception as exc:
        # Art. III — no exception reaches the runner; Art. III.4 — still logged.
        logger.error("Summariser failed: %s", exc)
        return (
            "The summariser is unavailable right now. Use the original text as it is "
            "rather than waiting for a shorter version."
        )

    summary = str(result).strip()
    if not summary:
        logger.error("Summariser returned an empty result")
        return (
            "The summariser returned nothing usable. Use the original text as it is."
        )
    return summary
