"""Terminal entry point for the Saylani Student Ops Desk (FR-1)."""

import asyncio
import sys

from agents import Runner
from agents.exceptions import InputGuardrailTripwireTriggered, MaxTurnsExceeded

from audit import AuditHooks
from config import MAX_TURNS, gemini_client
from desk_agent import desk_agent
from guardrail import CHECK_FAILED_MESSAGE, REFUSAL_MESSAGE, GuardrailCheckFailed
from run_support import run_with_retry
from student_profile import StudentProfile
from ticket import Ticket

EXIT_WORDS = {"exit", "quit"}


def build_profile() -> StudentProfile:
    """The single profile for this terminal session.

    Hardcoded test values for now; FR-12 builds one per Chainlit session instead.
    Constructing it here means invalid values fail before any run begins.
    """
    return StudentProfile(
        name="Shahid Khan",
        roll_no="SMIT-2026-0412",
        course_id="agentic-ai-w4",
        tier="regular",
        open_tickets=1,
    )


def print_ticket(ticket: Ticket) -> None:
    """Show the structured record, then branch on `resolved` (FR-7)."""
    print(f"Desk: {ticket.summary}\n")
    print("  --- ticket ---")
    print(f"  category : {ticket.category}")
    print(f"  summary  : {ticket.summary}")
    print(f"  next_step: {ticket.next_step}")
    print(f"  resolved : {ticket.resolved}")
    print(f"  escalate : {ticket.escalate}")

    # spec.md §4.7 — `resolved` drives behaviour, it is not merely displayed.
    if not ticket.resolved:
        if ticket.escalate:
            print("\n  I couldn't settle that one — a staff member will follow up.")
        else:
            print("\n  I couldn't settle that one. Add any detail you left out?")
    print()


async def _chat_loop(profile: StudentProfile) -> None:
    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not message:
            continue
        if message.lower() in EXIT_WORDS:
            return

        # FR-10 — one audit id per run, so a whole turn groups together.
        hooks = AuditHooks()

        try:
            result = await run_with_retry(
                lambda: Runner.run(
                    desk_agent,
                    message,
                    context=profile,  # FR-3 — student data reaches tools only here.
                    max_turns=MAX_TURNS,  # Art. VI.2
                    hooks=hooks,  # FR-10 — timeline into audit_log.jsonl
                )
            )
            ticket = result.final_output
            # FR-7 acceptance — checked in code, not eyeballed.
            assert type(ticket) is Ticket, (
                f"expected a Ticket, got {type(ticket).__name__}"
            )
            # FR-5 — which agent actually authored the reply the student sees.
            print(f"[answered by: {result.last_agent.name}]")
            print_ticket(ticket)
        except InputGuardrailTripwireTriggered as exc:
            # FR-8 — the single place the tripwire is caught (plan.md §5). No
            # Ticket exists for this turn: the Desk's model was never invoked.
            check = exc.guardrail_result.output.output_info
            reason = getattr(check, "reason", "no bootcamp-related intent")
            print(f"[refused by guardrail — {reason}]")
            print(f"Desk: {REFUSAL_MESSAGE}\n")
        except GuardrailCheckFailed:
            # spec.md §4.8 edge case — the check itself broke. Fail toward asking
            # for a rephrase, never toward answering an unchecked message.
            print("[guardrail could not run — message not passed to the Desk]")
            print(f"Desk: {CHECK_FAILED_MESSAGE}\n")
        except MaxTurnsExceeded:
            # Art. VI.2 / VIII.2 — graceful message, never a crash.
            print(
                "Desk: Sorry — that took more steps than I'm allowed. "
                "Could you rephrase it more simply?\n"
            )
        except Exception:
            # spec.md §4.1 — provider errors at call time are a runtime failure,
            # reported generically. The student never sees a traceback (Art. VIII.2).
            print(
                "Desk: Sorry — I'm temporarily unable to help. "
                "Please try again shortly.\n"
            )


async def main() -> None:
    profile = build_profile()
    print("Saylani Student Ops Desk — type 'exit' to leave.\n")
    try:
        await _chat_loop(profile)
    finally:
        # Close the HTTP connection pool so nothing is left pending when the
        # event loop tears down.
        await gemini_client.close()
    print("Goodbye.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Art. VIII.2 — a mid-run Ctrl+C exits quietly, never as a traceback.
        print("\nGoodbye.")
        sys.exit(0)
