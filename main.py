"""Terminal entry point for the Saylani Student Ops Desk (FR-1)."""

import asyncio

from agents import Runner
from agents.exceptions import MaxTurnsExceeded

from config import MAX_TURNS
from desk_agent import desk_agent

EXIT_WORDS = {"exit", "quit"}


async def main() -> None:
    print("Saylani Student Ops Desk — type 'exit' to leave.\n")

    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not message:
            continue
        if message.lower() in EXIT_WORDS:
            break

        try:
            result = await Runner.run(
                desk_agent,
                message,
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

    print("Goodbye.")


if __name__ == "__main__":
    asyncio.run(main())
