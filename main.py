"""Terminal entry point for the Saylani Student Ops Desk (FR-1)."""

import asyncio
import sys

from agents import RunContextWrapper, Runner
from agents.exceptions import MaxTurnsExceeded

from config import MAX_TURNS, gemini_client
from desk_agent import build_desk_instructions, desk_agent
from student_profile import StudentProfile

EXIT_WORDS = {"exit", "quit"}


def build_profile() -> StudentProfile:
    """The single profile for this terminal session.

    Hardcoded test values for now; FR-12 builds one per Chainlit session instead.
    Constructing it here means invalid values fail before any run begins.
    """
    return StudentProfile(
        name="Ayesha Khan",
        roll_no="SMIT-2026-0412",
        course_id="agentic-ai-w4",
        tier="regular",
        open_tickets=1,
    )


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

        # TODO(remove-before-phase-3): debug aid, not part of the spec — shows the
        # resolved FR-4 instructions before the model is called.
        print(
            "\n--- resolved instructions ---\n"
            f"{build_desk_instructions(RunContextWrapper(profile), desk_agent)}\n"
            "-----------------------------\n"
        )

        try:
            result = await Runner.run(
                desk_agent,
                message,
                context=profile,  # FR-3 — student data reaches tools only this way.
                max_turns=MAX_TURNS,  # Art. VI.2
            )
            reply = result.final_output
        except MaxTurnsExceeded:
            # Art. VI.2 / VIII.2 — graceful message, never a crash.
            reply = (
                "Sorry — that took more steps than I'm allowed. "
                "Could you rephrase it more simply?"
            )
        except Exception:
            # spec.md §4.1 — provider errors at call time are a runtime failure,
            # reported generically. The student never sees a traceback (Art. VIII.2).
            reply = "Sorry — I'm temporarily unable to help. Please try again shortly."

        print(f"Desk: {reply}\n")


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
