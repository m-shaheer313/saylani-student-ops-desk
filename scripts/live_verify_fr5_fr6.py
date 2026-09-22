"""Live gate for FR-5 (handoff routing) and FR-6 (Summariser-as-tool).

Makes exactly six live `Runner.run()` calls against the Desk and checks the agent
that authored each reply, plus the Summariser's line budget. Exits non-zero naming
the first failing case, so it can be used as a gate rather than read as a log.

Run from the project root:

    .venv\\Scripts\\python.exe scripts\\live_verify_fr5_fr6.py

Exit codes: 0 all cases passed; 1 an expectation failed; 2 could not reach the
model (e.g. Gemini quota), so nothing was proven either way.
"""

import asyncio
import sys
from pathlib import Path

# Project-relative import without requiring PYTHONPATH to be set.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import Runner  # noqa: E402
from agents.items import HandoffOutputItem, ToolCallItem, ToolCallOutputItem  # noqa: E402
from openai import APIError, InternalServerError, RateLimitError  # noqa: E402

from config import MAX_TURNS  # noqa: E402
from desk_agent import desk_agent  # noqa: E402
from guardrail import GuardrailCheckFailed  # noqa: E402
from student_profile import StudentProfile  # noqa: E402

# Free tier allows 5 requests per minute, and one case costs several (guardrail,
# Desk, any specialist or tool turn), so cases are spaced generously.
PAUSE_SECONDS = 75

# The model also returns transient 503s under load; retry rather than fail a case.
TRANSIENT_RETRIES = 3
TRANSIENT_BACKOFF_SECONDS = 70

SUMMARISER_TOOL = "summarise_policy"
CLOSE_TICKET_TOOL = "close_ticket"

# A policy long enough that summarising it is a real compression, not a no-op.
LONG_POLICY = """Submission window: assignments are accepted from the moment they are posted until 11:59pm on the stated due date, in the Asia/Karachi timezone only.
Late window: a submission arriving after the due date is accepted for a further 48 hours, and a flat 20 percent penalty is applied to whatever mark it earns.
Hard cutoff: beyond that 48 hour window nothing is accepted, the assignment is recorded as zero, and no instructor has discretion to reopen it.
Attendance: a student must hold at least 80 percent attendance across the whole module to be eligible to sit the final assessment.
Appeals: attendance and late-penalty decisions may be appealed in writing, but only while the module is still open; once it closes the record is final.
Resubmission: one resubmission per assignment is permitted inside the original submission window, and the later attempt replaces the earlier one entirely."""

SHORT_POLICY = "Late work is accepted for 48 hours with a flat 20 percent penalty."


def _tool_outputs(result, tool_name: str) -> list[str]:
    """Return the outputs of every call to `tool_name` in this run."""
    call_ids = {
        item.raw_item.call_id
        for item in result.new_items
        if isinstance(item, ToolCallItem)
        and getattr(item.raw_item, "name", None) == tool_name
    }
    outputs = []
    for item in result.new_items:
        if not isinstance(item, ToolCallOutputItem):
            continue
        raw = item.raw_item
        call_id = raw.get("call_id") if isinstance(raw, dict) else getattr(raw, "call_id", None)
        if call_id in call_ids:
            outputs.append(str(item.output))
    return outputs


def _tool_call_names(result) -> list[str]:
    """Every tool the model invoked in this run, in order."""
    return [
        name
        for item in result.new_items
        if isinstance(item, ToolCallItem)
        and (name := getattr(item.raw_item, "name", None)) is not None
    ]


def _check_close_ticket(case: str, result) -> str | None:
    """FR-9b — the run must have ended through close_ticket, not plain output.

    Deliberately independent of the routing check: a dormant stopping rule is a
    close_ticket defect, not a handoff defect, and must be reported as such.
    """
    names = _tool_call_names(result)
    if CLOSE_TICKET_TOOL in names:
        return None
    return (
        f"{case}: close_ticket was never called — the FR-9b stopping rule is "
        f"dormant; the model produced its Ticket via plain structured output "
        f"instead (tool calls seen: {names or 'none'})"
    )


def _handoff_names(result) -> list[str]:
    return [
        item.target_agent.name
        for item in result.new_items
        if isinstance(item, HandoffOutputItem)
    ]


async def _ask(profile: StudentProfile, message: str):
    """Run one turn, retrying only transient rate-limit/overload responses."""
    for attempt in range(1, TRANSIENT_RETRIES + 1):
        try:
            return await Runner.run(
                desk_agent, message, context=profile, max_turns=MAX_TURNS
            )
        except (RateLimitError, InternalServerError, GuardrailCheckFailed) as exc:
            # GuardrailCheckFailed here means the guardrail's own model call hit
            # the same transient limit — not a verdict about the message.
            if attempt == TRANSIENT_RETRIES:
                raise
            label = type(exc).__name__
            print(f"  (transient {label}, waiting {TRANSIENT_BACKOFF_SECONDS}s)")
            await asyncio.sleep(TRANSIENT_BACKOFF_SECONDS)
    raise RuntimeError("unreachable")


def _check_agent(case: str, result, expected: str) -> str | None:
    """Return a failure description, or None if the case passed."""
    actual = result.last_agent.name
    if actual != expected:
        return f"{case}: expected last_agent {expected!r}, got {actual!r}"
    return None


def _check_summary(case: str, result, source_text: str | None = None) -> str | None:
    """Check the Summariser's line budget, and that short input was not padded."""
    outputs = _tool_outputs(result, SUMMARISER_TOOL)
    if not outputs:
        used = [
            i.raw_item.name for i in result.new_items if isinstance(i, ToolCallItem)
        ]
        return (
            f"{case}: no {SUMMARISER_TOOL} output in this run "
            f"(tool calls seen: {used or 'none'})"
        )

    for output in outputs:
        lines = [ln for ln in output.splitlines() if ln.strip()]
        print(f"    tool returned {len(lines)} non-blank line(s):")
        for ln in lines:
            print(f"      | {ln}")
        if len(lines) > 3:
            return f"{case}: summariser returned {len(lines)} lines, limit is 3"

        # spec.md §4.6: already-short input must not be padded. Allow a little
        # slack for rewording, but not growth into a longer restructured answer.
        if source_text is not None:
            budget = int(len(source_text.strip()) * 1.2)
            if len(output.strip()) > budget:
                return (
                    f"{case}: summariser padded a short input — "
                    f"{len(output.strip())} chars out vs {len(source_text.strip())} in "
                    f"(budget {budget})"
                )
    return None


async def main() -> int:
    profile = StudentProfile(
        name="Shahid Khan",
        roll_no="SMIT-2026-0412",
        course_id="agentic-ai-w4",
        tier="regular",
        open_tickets=1,
    )

    failures: list[str] = []

    # (label, message, primary check, does this case end in a Ticket?)
    cases = [
        (
            "1 assignment-only",
            "When is assignment a3 due?",
            lambda c, r: _check_agent(c, r, "Assignments Specialist"),
            True,
        ),
        (
            "2 career-only",
            "Should I focus on Python or Go for job hunting?",
            lambda c, r: _check_agent(c, r, "Careers Specialist"),
            True,
        ),
        (
            "3 admin-only",
            "What courses do you offer?",
            lambda c, r: _check_agent(c, r, "Ops Desk"),
            True,
        ),
        (
            "4 assignment+career tie",
            "Will finishing my assignments actually help me get a job, and is a3 "
            "still open?",
            lambda c, r: _check_agent(c, r, "Assignments Specialist"),
            True,
        ),
        (
            "5 summariser, long input",
            "Use your summarise_policy tool to shorten the policy text below, then "
            "relay the short version to me. Do not hand this off to anyone.\n\n"
            f"{LONG_POLICY}",
            _check_summary,
            False,
        ),
        (
            "6 summariser, already-short input",
            "Use your summarise_policy tool on exactly this one line, then relay the "
            "result. Do not hand this off to anyone.\n\n"
            f"{SHORT_POLICY}",
            lambda c, r: _check_summary(c, r, source_text=SHORT_POLICY),
            False,
        ),
    ]

    for index, (case, message, check, ends_in_ticket) in enumerate(cases):
        print(f"\n=== {case} ===")
        print(f"  sent   : {message.splitlines()[0][:100]}")

        try:
            result = await _ask(profile, message)
        except (APIError, GuardrailCheckFailed) as exc:
            print(f"  BLOCKED: could not reach the model — {exc}")
            print("\nNothing was proven; rerun when the model is reachable.")
            return 2

        print(f"  agent  : {result.last_agent.name}")
        handoffs = _handoff_names(result)
        print(f"  handoff: {handoffs if handoffs else 'none'}")
        print(f"  tools  : {_tool_call_names(result) or 'none'}")
        print(f"  reply  : {str(result.final_output).strip()[:400]}")

        # Two independent verdicts, so a dormant stopping rule never reads as a
        # routing failure (or vice versa).
        primary = check(case, result)
        print(f"  routing: {'pass' if primary is None else f'FAIL — {primary}'}")
        if primary:
            failures.append(primary)

        if ends_in_ticket:
            stopping = _check_close_ticket(case, result)
            print(
                f"  closing: {'pass' if stopping is None else f'FAIL — {stopping}'}"
            )
            if stopping:
                failures.append(stopping)

        if index < len(cases) - 1:
            await asyncio.sleep(PAUSE_SECONDS)

    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED ({len(failures)} assertion(s) across {len(cases)} cases):")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"PASSED — all {len(cases)} cases met every expectation.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
