"""Chainlit interface for the Saylani Student Ops Desk (FR-12, plan.md §11).

All per-conversation state — the student's profile and the running history —
lives in `cl.user_session`. Nothing is held in a module-level variable, so two
browser sessions are isolated by construction (spec.md §4.12).
"""

import chainlit as cl
from agents import RunConfig, Runner
from agents.exceptions import InputGuardrailTripwireTriggered, MaxTurnsExceeded

from audit import AuditHooks
from config import MAX_TURNS, WORKFLOW_NAME
from desk_agent import desk_agent
from guardrail import CHECK_FAILED_MESSAGE, REFUSAL_MESSAGE, GuardrailCheckFailed
from run_support import run_with_retry
from student_profile import StudentProfile
from ticket import Ticket
from tools import lookup_course_title

PROFILE_KEY = "profile"
HISTORY_KEY = "history"


def build_profile() -> StudentProfile:
    """The one profile for this browser session.

    Hardcoded test values: there is no login flow in this iteration (NG-2 — the
    student is always already identified). Constructing it here means an invalid
    tier or negative ticket count fails when the session opens, before any run.
    """
    return StudentProfile(
        name="Shaheer",
        roll_no="SMIT-2026-0412",
        course_id="agentic-ai-w4",
        tier="regular",
        open_tickets=1,
    )


def format_ticket(ticket: Ticket, docket_ref: str) -> str:
    """The reply, followed by the docket stub the student keeps.

    The stub is a markdown table so the styling in public/style.css hangs off
    markup this app controls, not off Chainlit's internal class names.
    """
    status = "Resolved" if ticket.resolved else "*Open*"
    escalated = "*Yes — staff notified*" if ticket.escalate else "No"

    lines = [
        ticket.summary,
        "",
        f"**Next step:** {ticket.next_step}",
        "",
        f"| Docket | {docket_ref} |",
        "| --- | --- |",
        f"| Category | {ticket.category} |",
        f"| Status | {status} |",
        f"| Escalated | {escalated} |",
    ]

    # spec.md §4.7 — `resolved` drives behaviour, not just display.
    if not ticket.resolved:
        lines += [
            "",
            "A staff member will pick this up and follow up with you."
            if ticket.escalate
            else "Tell me a bit more and I'll try again.",
        ]
    return "\n".join(lines)


@cl.set_starters
async def starters() -> list[cl.Starter]:
    """Four openers covering the desk's four categories."""
    return [
        cl.Starter(
            label="Check a deadline",
            message="When is assignment a3 due?",
            icon="/public/icons/deadline.svg",
        ),
        cl.Starter(
            label="Read a policy",
            message="What happens if I submit an assignment late?",
            icon="/public/icons/policy.svg",
        ),
        cl.Starter(
            label="Plan a career step",
            message="What should I learn next to get hired as a developer?",
            icon="/public/icons/career.svg",
        ),
        cl.Starter(
            label="See my account",
            message="What is my account status?",
            icon="/public/icons/account.svg",
        ),
    ]


@cl.on_chat_start
async def on_chat_start() -> None:
    """Build this session's profile and empty history, session-scoped only."""
    cl.user_session.set(PROFILE_KEY, build_profile())
    cl.user_session.set(HISTORY_KEY, [])

    profile: StudentProfile = cl.user_session.get(PROFILE_KEY)
    course = lookup_course_title(profile.course_id) or "your course"
    await cl.Message(
        content=(
            f"The desk is open, {profile.name or 'Student'} — you're enrolled in "
            f"{course}. Every answer comes with a docket you can quote to staff."
        ),
        author="Ops Desk",
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Run one turn for this session and render the resulting Ticket."""
    profile: StudentProfile = cl.user_session.get(PROFILE_KEY)
    history: list = cl.user_session.get(HISTORY_KEY) or []

    if profile is None:
        # Defensive: a message arriving before on_chat_start ran.
        profile = build_profile()
        cl.user_session.set(PROFILE_KEY, profile)

    # The run sees this session's prior turns, so a follow-up that refers back
    # ("what about the one after that?") resolves correctly (spec.md §4.12).
    run_input = history + [{"role": "user", "content": message.content}]

    # FR-10 — a fresh audit id per run, exactly as the terminal loop does.
    hooks = AuditHooks()

    try:
        # `await` the async run: returning before it completes would show the
        # student a blank or premature reply (spec.md §4.12).
        result = await run_with_retry(
            lambda: Runner.run(
                desk_agent,
                run_input,
                context=profile,
                max_turns=MAX_TURNS,
                hooks=hooks,
                # FR-13 — one trace per turn, filed under the same id as this
                # turn's audit timeline and the docket shown to the student.
                run_config=RunConfig(
                    workflow_name=WORKFLOW_NAME,
                    group_id=hooks.request_id,
                ),
            )
        )
    except InputGuardrailTripwireTriggered:
        # FR-8 — refused before the Desk's model ran; no Ticket, history unchanged.
        await cl.Message(content=REFUSAL_MESSAGE).send()
        return
    except GuardrailCheckFailed:
        # spec.md §4.8 edge case — the check itself broke; ask for a rephrase
        # rather than answering an unchecked message.
        await cl.Message(content=CHECK_FAILED_MESSAGE).send()
        return
    except MaxTurnsExceeded:
        # Art. VI.2 / VIII.2 — graceful, never a traceback in the browser.
        await cl.Message(
            content=(
                "Sorry — that took more steps than I'm allowed. Could you "
                "rephrase it more simply?"
            )
        ).send()
        return
    except Exception:
        await cl.Message(
            content=(
                "Sorry — I'm temporarily unable to help. Please try again shortly."
            )
        ).send()
        return

    ticket = result.final_output
    if not isinstance(ticket, Ticket):
        await cl.Message(
            content="Sorry — I couldn't produce a proper answer for that one."
        ).send()
        return

    # Only a completed run updates this session's history.
    cl.user_session.set(HISTORY_KEY, result.to_input_list())

    # author = the agent that actually wrote the reply, so a handoff is visible
    # in the transcript itself rather than only mentioned in the text.
    # The audit id doubles as the docket number the student can quote to staff.
    await cl.Message(
        content=format_ticket(ticket, hooks.request_id[:8]),
        author=result.last_agent.name,
    ).send()
